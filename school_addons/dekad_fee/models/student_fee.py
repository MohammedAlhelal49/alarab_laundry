from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DeStudentFee(models.Model):
    _name = "de.student.fee"
    _description = "Student Fees"
    _rec_name = 'student_id'


    fee_term_line_id = fields.Many2one('de.fee.term.line', 'Fees term line')
    amount = fields.Monetary('Fees Amount', currency_field='currency_id')
    date = fields.Date('Due Date')
    student_id = fields.Many2one('de.student', 'Student', ondelete="cascade")
    fees_factor = fields.Integer("Fees Factor")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('invoice', 'Invoice Created')
    ], string='Status', default="draft")

    after_discount_amount = fields.Monetary(compute="_compute_discount_amount",
                                            currency_field='currency_id',
                                            string='After Discount Amount')
    discount = fields.Float(string='Discount (%)',
                            digits='Discount', default=0.0)

    grade_id = fields.Many2one('de.grade', 'Grade', required=True)
    product_id = fields.Many2one('product.product', 'Product')
    invoice_id = fields.Many2one('account.move', 'Invoice ID')
    invoice_state = fields.Selection(related="invoice_id.state",
                                     string='Invoice Status',
                                     readonly=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id.id)

    @api.depends('discount')
    def _compute_discount_amount(self):
        for discount in self:
            discount_amount = discount.amount * discount.discount / 100.0
            discount.after_discount_amount = discount.amount - discount_amount

    def _get_or_create_student_fee_journal(self):
        """Get or create a journal for student fees"""
        journal = self.env['account.journal'].search([
            ('code', '=', 'STF'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not journal:
            try:
                journal = self.env['account.journal'].create({
                    'name': 'Student Fees',
                    'code': 'STF',
                    'type': 'sale',  # Use sale type for customer invoices
                    'company_id': self.env.company.id,
                })
            except Exception as e:
                # Fallback to any existing sale journal
                journal = self.env['account.journal'].search([
                    ('type', '=', 'sale'),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)

                if not journal:
                    raise UserError(
                        _('No suitable journal found for student fees. '
                          'Please create a sales journal or contact administrator.'))

        return journal

    def _get_account_from_product(self, product):
        """Try to get account from product, with fallbacks"""
        account_id = False

        # Try product income account
        try:
            if hasattr(product, 'property_account_income_id') and product.property_account_income_id:
                account_id = product.property_account_income_id.id
        except:
            pass

        # Try product category income account
        if not account_id:
            try:
                if (hasattr(product, 'categ_id') and product.categ_id and
                        hasattr(product.categ_id, 'property_account_income_categ_id') and
                        product.categ_id.property_account_income_categ_id):
                    account_id = product.categ_id.property_account_income_categ_id.id
            except:
                pass

        # If still no account, try to find any income account
        if not account_id:
            try:
                income_account = self.env['account.account'].search([
                    ('account_type', 'in', ['income', 'income_other']),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)

                if income_account:
                    account_id = income_account.id
            except:
                pass

        # Final fallback - use any available account
        if not account_id:
            try:
                any_account = self.env['account.account'].search([
                    ('company_id', '=', self.env.company.id)
                ], limit=1)

                if any_account:
                    account_id = any_account.id
            except:
                pass

        return account_id

    def create_invoice(self):
        """Create invoice for fee payment process of student using journal"""
        try:
            # Get the journal for student fees
            journal = self._get_or_create_student_fee_journal()

            inv_obj = self.env['account.move']
            partner_id = self.student_id.partner_id
            product = self.product_id

            # Get account from product with fallbacks
            account_id = self._get_account_from_product(product)

            if not account_id:
                # Create invoice without specifying account - let Odoo handle it
                return self._create_invoice_without_account(journal)

            amount = self.amount
            name = product.name

            # Check for fee elements
            element_id = self.env['de.fee.element'].search([
                ('fee_term_line_id', '=', self.fee_term_line_id.id)])

            invoice_line_list = []
            if element_id:
                for records in element_id:
                    # Try to get account for each element
                    element_account_id = self._get_account_from_product(records.product_id)
                    if not element_account_id:
                        element_account_id = account_id  # Use main account as fallback

                    line_data = {
                        'name': records.product_id.name,
                        'price_unit': records.value * self.amount / 100,
                        'quantity': 1.0,
                        'discount': self.discount or False,
                        'product_uom_id': records.product_id.uom_id.id,
                        'product_id': records.product_id.id,
                    }

                    # Only add account if we have one
                    if element_account_id:
                        line_data['account_id'] = element_account_id

                    invoice_line_list.append((0, 0, line_data))
            else:
                line_data = {
                    'name': name,
                    'price_unit': amount,
                    'quantity': 1.0,
                    'discount': self.discount or False,
                    'product_uom_id': product.uom_id.id,
                    'product_id': product.id
                }

                # Only add account if we have one
                if account_id:
                    line_data['account_id'] = account_id

                invoice_line_list.append((0, 0, line_data))

            # Create invoice with the specific journal
            invoice_data = {
                'move_type': 'out_invoice',
                'journal_id': journal.id,  # Specify the journal
                'partner_id': partner_id.id,
                'invoice_line_ids': invoice_line_list,
            }

            invoice = inv_obj.create(invoice_data)

            # Compute tax totals if method exists
            if hasattr(invoice, '_compute_tax_totals'):
                invoice._compute_tax_totals()

            self.state = 'invoice'
            self.invoice_id = invoice.id
            return True

        except Exception as e:
            raise UserError(
                _('Error creating invoice: %s\n\n'
                  'This might be due to missing accounting configuration. '
                  'Please ensure:\n'
                  '1. You have the Invoicing module installed\n'
                  '2. Your products have proper accounting setup\n'
                  '3. Or contact your administrator') % str(e))

    def _create_invoice_without_account(self, journal):
        """Create invoice without specifying accounts - let Odoo handle it"""
        try:
            inv_obj = self.env['account.move']
            partner_id = self.student_id.partner_id
            product = self.product_id

            # Check for fee elements
            element_id = self.env['de.fee.element'].search([
                ('fee_term_line_id', '=', self.fee_term_line_id.id)])

            invoice_line_list = []
            if element_id:
                for records in element_id:
                    invoice_line_list.append((0, 0, {
                        'name': records.product_id.name,
                        'price_unit': records.value * self.amount / 100,
                        'quantity': 1.0,
                        'discount': self.discount or False,
                        'product_id': records.product_id.id,
                        # Let Odoo automatically determine account from product
                    }))
            else:
                invoice_line_list.append((0, 0, {
                    'name': product.name,
                    'price_unit': self.amount,
                    'quantity': 1.0,
                    'discount': self.discount or False,
                    'product_id': product.id,
                    # Let Odoo automatically determine account from product
                }))

            # Create invoice
            invoice = inv_obj.create({
                'move_type': 'out_invoice',
                'journal_id': journal.id,
                'partner_id': partner_id.id,
                'invoice_line_ids': invoice_line_list,
            })

            # Compute tax totals if method exists
            if hasattr(invoice, '_compute_tax_totals'):
                invoice._compute_tax_totals()

            self.state = 'invoice'
            self.invoice_id = invoice.id
            return True

        except Exception as e:
            raise UserError(
                _('Cannot create invoice even with automatic account detection: %s\n\n'
                  'Please ensure your products are properly configured or '
                  'contact your administrator.') % str(e))

    def action_show_invoice(self):
        if not self.invoice_id:
            raise UserError(_('No invoice has been created yet.'))

        try:
            form_view = self.env.ref('account.view_move_form')
        except ValueError:
            # Fallback if specific views don't exist
            form_view = False

        return {
            'name': 'Student Fee Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'view_id': form_view.id if form_view else False,
            'target': 'current',
            'context': {'create': False, 'edit': False}
        }


class DeStudent(models.Model):
    _inherit = "de.student"

    student_fee_ids = fields.One2many('de.student.fee',
                                      'student_id',
                                      string='Fees Collection Details',
                                      tracking=True)

    student_fee_count = fields.Integer('Fees count',
                                       compute='_compute_student_fee_count',
                                       readonly=True, store=True)

    @api.depends('student_fee_ids')
    def _compute_student_fee_count(self):
        for rec in self:
            rec.student_fee_count = len(rec.student_fee_ids)

    def action_show_fee(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fees Details',
            'view_mode': 'list,form',
            'res_model': 'de.student.fee',
            'context': {'create': False},
            'domain': [('student_id', '=', self.id)],
            'target': 'current',
        }

    def action_show_invoice(self):
        """Show all invoices created from student fees"""
        invoice_ids = []
        for fee in self.student_fee_ids:
            if fee.invoice_id:
                invoice_ids.append(fee.invoice_id.id)

        if not invoice_ids:
            raise UserError(_('No invoices have been created for this student yet.'))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Student Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoice_ids)],
            'context': {'default_partner_id': self.partner_id.id if self.partner_id else False},
            'target': 'current',
        }


class DeStudentGrade(models.Model):
    _inherit = "de.student.grade"

    fee_term_id = fields.Many2one('de.fee.term', 'Fees Terms')
    product_id = fields.Many2one('product.product', 'Register fee')
    fee_start_date = fields.Date('fee Start Date')