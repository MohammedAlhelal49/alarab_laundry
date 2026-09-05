# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.http import request
from datetime import timedelta, date
from pytz import timezone
from datetime import datetime


class Attachment(models.Model):
    _inherit = 'ir.attachment'

    pdc_id = fields.Many2one('pdc.wizard')


class PDCWizard(models.Model):
    _name = "pdc.wizard"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "PDC Wizard"

    # pdc only be allowed to delete in draft state
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError("You can only delete draft state PDC.")

            if (
                    not self.env.user.has_group('sh_pdc.group_pdc_admin')
                    and rec.user_id != self.env.user
            ):
                raise UserError("You can only delete your own draft PDC.")

        return super().unlink()


    def _check_pdc_admin(self):
        if not self.env.user.has_group('sh_pdc.group_pdc_admin'):
            raise UserError("Only PDC Administrators can perform this action.")


    def action_register_check(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        account_move_model = self.env[active_model].browse(active_id)

        if account_move_model.move_type not in ('out_invoice', 'in_invoice'):
            raise UserError(
                "Only Customer invoice and vendor bills are considered!")

        move_listt = []
        payment_amount = 0.0
        payment_type = ''
        if len(active_ids) > 0:
            account_moves = self.env[active_model].browse(active_ids)
            partners = account_moves.mapped('partner_id')
            if len(set(partners)) != 1:
                raise UserError('Partners must be same')

            states = account_moves.mapped('state')
            if len(set(states)) != 1 or states[0] != 'posted':
                raise UserError(
                    'Only posted invoices/bills are considered for PDC payment!!')

            for account_move in account_moves:
                if account_move.payment_state != 'paid' and account_move.amount_residual != 0.0:
                    payment_amount = payment_amount + account_move.amount_residual
                    move_listt.append(account_move.id)
        if not move_listt:
            raise UserError("Selected invoices/bills are already paid!!")

        if account_moves[0].move_type in ('in_invoice'):
            payment_type = 'send_money'

        if account_moves[0].move_type in ('out_invoice'):
            payment_type = 'receive_money'

        return {
            'name': 'PDC Payment',
            'res_model': 'pdc.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('sh_pdc.sh_pdc_wizard_form_wizard').id,
            'context': {
                'default_invoice_ids': [(6, 0, move_listt)],
                'default_partner_id': account_move_model.partner_id.id,
                'default_payment_amount': payment_amount,
                'default_payment_type': payment_type
            },
            'target': 'new',
            'type': 'ir.actions.act_window'
        }

    def button_register(self):
        listt = []
        if self:
            if self.invoice_id:
                listt.append(self.invoice_id.id)
            if self.invoice_ids:
                listt.extend(self.invoice_ids.ids)

            self.write({
                'invoice_ids': [(6, 0, list(set(listt)))]
            })

            if self.cheque_status == 'draft':
                self.write({'state': 'draft'})

            if self.cheque_status == 'new':
                self.action_register()
                self.write({'state': 'registered'})

            if self.cheque_status == 'deposit':
                self.action_register()
                self.action_deposited()
                self.write({'state': 'deposited'})

            if self.cheque_status == 'paid':
                self.action_register()
                self.action_deposited()
                self.action_done()
                self.write({'state': 'done'})

    def open_journal_items(self):
        [action] = self.env.ref('account.action_account_moves_all').read()
        ids = self.env['account.move.line'].search([('pdc_id', '=', self.id)])
        id_list = []
        for pdc_id in ids:
            id_list.append(pdc_id.id)
        if id_list:
            action['domain'] = [('id', 'in', id_list)]
        else:
            action['domain'] = [('id', '=', False)]
        return action

    def open_journal_entry(self):
        [action] = self.env.ref(
            'sh_pdc.sh_pdc_action_move_journal_line').read()
        ids = self.env['account.move'].search([('pdc_id', '=', self.id)])
        id_list = []
        for pdc_id in ids:
            id_list.append(pdc_id.id)
        action['domain'] = [('id', 'in', id_list)]
        return action

    @api.model
    def default_get(self, fields):
        rec = super().default_get(fields)
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec
        invoices = self.env['account.move'].browse(active_ids)
        if invoices and len(invoices) == 1:
            invoice = invoices[0]
            if invoice.move_type in ('out_invoice', 'out_refund'):
                rec.update({'payment_type': 'receive_money'})
            elif invoice.move_type in ('in_invoice', 'in_refund'):
                rec.update({'payment_type': 'send_money'})

            rec.update({'partner_id': invoice.partner_id.id,
                        'payment_amount': invoice.amount_residual,
                        'invoice_id': invoice.id,
                        'due_date': invoice.invoice_date_due,
                        'memo': invoice.name})

        return rec

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('payment_type') == 'receive_money':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pdc.payment.customer')
            elif vals.get('payment_type') == 'send_money':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pdc.payment.vendor')

        res = super().create(vals_list)
        res.attachment_ids.write({
            'res_id': res.id
        })
        return res

    name = fields.Char("Name", default='New', readonly=True, tracking=True)
    payment_type = fields.Selection([('receive_money', 'Receive Money'), (
        'send_money', 'Send Money')], string="Payment Type", default='receive_money', tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string="Partner", tracking=True)
    payment_amount = fields.Monetary("Payment Amount", tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string="Currency", default=lambda self: self.env.company.currency_id, tracking=True)
    reference = fields.Char("Cheque Reference", tracking=True)
    journal_id = fields.Many2one('account.journal', string="Payment Journal", domain=[
        ('type', '=', 'bank')], required=True, tracking=True)
    cheque_status = fields.Selection([('draft', 'Draft'), ('new', 'New'), ('deposit', 'Registered'), (
        'paid', 'Paid')], string="Cheque Status", default='draft', tracking=True)
    payment_date = fields.Date(
        "Payment Date", default=fields.Date.today(), required=True, tracking=True)
    due_date = fields.Date("Due Date", tracking=True)
    memo = fields.Char("Memo", tracking=True)
    agent = fields.Char("Agent", tracking=True)
    bank_id = fields.Many2one('res.bank', string="Bank", tracking=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'pdc_attachment_rel', string='Cheque Attachments')
    company_id = fields.Many2one(
        'res.company', string='company', default=lambda self: self.env.company, tracking=True)
    invoice_id = fields.Many2one(
        'account.move', string="Invoice/Bill", tracking=True)
    invoice_ids = fields.Many2many('account.move')
    state = fields.Selection([('draft', 'Draft'), ('registered', 'New'), ('returned', 'Returned'),
                              ('deposited', 'Registered'), ('bounced', 'Bounced'), ('done', 'Done'),
                              ('cancel', 'Cancelled')], string="State", default='draft', tracking=True)

    deposited_debit = fields.Many2one('account.move.line')
    deposited_credit = fields.Many2one('account.move.line')

    account_move_ids = fields.Many2many(
        'account.move', compute="compute_account_moves", )
    done_date = fields.Date(string="Done Date", tracking=True)
    customer_account = fields.Many2one('account.account', string="Receive money account",
                                       )
    vendor_account = fields.Many2one('account.account', string="Send money account",
                                     )

    is_warranty_cheque = fields.Boolean(string="Warranty Cheque", tracking=True)
    user_id = fields.Many2one(
        'res.users',
        string='Created By',
        related='create_uid',
        readonly=True,
    )
    pdc_image = fields.Image(
        string='PDC Image',
        max_width=1920,
        max_height=1920,
        help="Upload a clear, landscape photo of the full cheque. JPG or PNG, max 1920 × 1080 px."
    )

    @api.depends('payment_type', 'partner_id')
    def compute_account_moves(self):

        self.account_move_ids = False
        domain = [('partner_id', '=', self.partner_id.id), ('payment_state', '!=',
                                                            'paid'), ('amount_residual', '!=', 0.0),
                  ('state', '=', 'posted')]

        if self.payment_type == 'receive_money':
            domain.extend([('move_type', '=', 'out_invoice')])

        else:
            domain.extend([('move_type', '=', 'in_invoice')])

        moves = self.env['account.move'].search(domain)
        self.account_move_ids = moves.ids

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        for rec in self:
            if rec.invoice_ids:
                if (rec.payment_type == 'send_money' and rec.invoice_ids[0].move_type == 'out_invoice') or (
                        rec.payment_type == 'receive_money' and rec.invoice_ids[0].move_type == 'in_invoice'):
                    raise UserError(
                        "You cant change the Payment type if you register the pdc cheque from an invoice or bill")

    @api.onchange('partner_id')
    def _onchange_partner(self):
        for rec in self:
            if rec.invoice_ids:
                if not rec.partner_id or rec.partner_id != rec.invoice_ids[0].partner_id:
                    raise UserError(
                        "You cant change the Partner if you register the pdc cheque from an invoice or bill")

            if rec.partner_id:
                if not rec.customer_account:
                    rec.customer_account = rec.partner_id.property_account_receivable_id
                if not rec.vendor_account:
                    rec.vendor_account = rec.partner_id.property_account_payable_id
        if self.env.company.auto_fill_open_invoice:

            domain = [('partner_id', '=', self.partner_id.id), ('payment_state', '!=',
                                                                'paid'), ('amount_residual', '!=', 0.0),
                      ('state', '=', 'posted')]

            if self.payment_type == 'receive_money':
                domain.extend([('move_type', '=', 'out_invoice')])

            else:
                domain.extend([('move_type', '=', 'in_invoice')])

            moves = self.env['account.move'].search(domain)

            self.invoice_ids = [(6, 0, moves.ids)]

    def action_register(self):
        self.check_payment_amount()

        if self.invoice_ids:
            list_amount_residuals = self.invoice_ids.mapped('amount_residual')
            amount = (self.currency_id.round(sum(list_amount_residuals))
                      if self.currency_id else round(sum(list_amount_residuals), 2))

            if self.payment_amount > amount and amount != 0:
                raise UserError(
                    "Payment amount is greater than total invoice/bill amount!!!")

        self.write({'state': 'registered'})

    def check_payment_amount(self):
        if self.payment_amount <= 0.0:
            raise UserError("Amount must be greater than zero!")

    def check_pdc_account(self):
        if self.payment_type == 'receive_money':
            if not self.env.company.pdc_customer:
                raise UserError(
                    "Please Set PDC payment account for Customer !")
            else:
                return self.env.company.pdc_customer.id

        else:
            if not self.env.company.pdc_vendor:
                raise UserError(
                    "Please Set PDC payment account for Supplier !")
            else:
                return self.env.company.pdc_vendor.id

    def get_partner_account(self):
        if self.payment_type == 'receive_money':
            account = self.customer_account or self.partner_id.property_account_receivable_id
        else:
            account = self.vendor_account or self.partner_id.property_account_payable_id
        if not account:
            raise UserError("Partner is missing a valid receivable or payable account.")
        return account.id

    def action_returned(self):
        self.check_payment_amount()
        self.write({'state': 'returned'})

    def get_debit_move_line(self, account):
        if not account:
            raise UserError("Missing debit account for PDC transaction.")
        return {
            'pdc_id': self.id,
            'account_id': account,
            'debit': self.payment_amount,
            'ref': self.memo,
            'date': self.done_date or self.payment_date if self.state == 'deposited' else self.payment_date,
            'date_maturity': self.done_date or self.due_date,
        }

    def get_credit_move_line(self, account):
        if not account:
            raise UserError("Missing credit account for PDC transaction.")
        return {
            'pdc_id': self.id,
            'account_id': account,
            'credit': self.payment_amount,
            'ref': self.memo,
            'date': self.done_date or self.payment_date if self.state == 'deposited' else self.payment_date,
            'date_maturity': self.done_date or self.due_date,
        }

    def get_move_vals(self, debit_line, credit_line):
        return {
            'pdc_id': self.id,
            'date': self.done_date or self.payment_date if self.state == 'deposited' else self.payment_date,
            'journal_id': self.journal_id.id,
            'partner_id': self.partner_id and self.partner_id.id,
            'ref': self.memo,
            'move_type': 'entry',
            'line_ids': [(0, 0, debit_line),
                         (0, 0, credit_line)]
        }

    def action_deposited(self):
        self._check_pdc_admin()

        for rec in self:
            if not rec.due_date:
                raise UserError("Please set Due Date before clicking Register.")

        move = self.env['account.move']

        self.check_payment_amount()  # amount must be positive
        pdc_account = self.check_pdc_account()
        partner_account = self.get_partner_account()

        # Create Journal Item
        move_line_vals_debit = {}
        move_line_vals_credit = {}
        if self.payment_type == 'receive_money':
            move_line_vals_debit = self.get_debit_move_line(pdc_account)
            move_line_vals_credit = self.get_credit_move_line(partner_account)
        else:
            move_line_vals_debit = self.get_debit_move_line(partner_account)
            move_line_vals_credit = self.get_credit_move_line(pdc_account)

        # create move and post it
        move_vals = self.get_move_vals(
            move_line_vals_debit, move_line_vals_credit)

        if self.invoice_ids:
            total_amount_residuals = sum(
                self.invoice_ids.mapped('amount_residual'))
            if total_amount_residuals != 0:
                move_id = move.create(move_vals)
                move_id.action_post()
                self.write({'deposited_debit': move_id.line_ids.filtered(lambda x: x.debit > 0),
                            'deposited_credit': move_id.line_ids.filtered(lambda x: x.credit > 0)})
        else:
            move_id = move.create(move_vals)
            move_id.action_post()
            self.write({'deposited_debit': move_id.line_ids.filtered(lambda x: x.debit > 0),
                        'deposited_credit': move_id.line_ids.filtered(lambda x: x.credit > 0)})

        self.write({
            'state': 'deposited',
        })

        self.reset_account_pdc_config_partner()

    def action_bounced(self):
        self._check_pdc_admin()

        move = self.env['account.move']

        self.check_payment_amount()  # amount must be positive
        pdc_account = self.check_pdc_account()
        partner_account = self.get_partner_account()

        # Create Journal Item
        move_line_vals_debit = {}
        move_line_vals_credit = {}

        if self.payment_type == 'receive_money':
            move_line_vals_debit = self.get_debit_move_line(partner_account)
            move_line_vals_credit = self.get_credit_move_line(pdc_account)
        else:
            move_line_vals_debit = self.get_debit_move_line(pdc_account)
            move_line_vals_credit = self.get_credit_move_line(partner_account)

        if self.memo:
            move_line_vals_debit.update({'name': 'PDC Payment :' + self.memo})
            move_line_vals_credit.update({'name': 'PDC Payment :' + self.memo})
        else:
            move_line_vals_debit.update({'name': 'PDC Payment'})
            move_line_vals_credit.update({'name': 'PDC Payment'})
        # create move and post it
        move_vals = self.get_move_vals(
            move_line_vals_debit, move_line_vals_credit)

        if self.invoice_ids:
            total_amount_residuals = sum(
                self.invoice_ids.mapped('amount_residual'))
            if total_amount_residuals != 0:
                move_id = move.create(move_vals)
                move_id.action_post()

        else:
            move_id = move.create(move_vals)
            move_id.action_post()

        self.write({
            'state': 'bounced',
        })

        self.reset_account_pdc_config_partner()

    # form view cancel button
    def action_cancel(self):
        self.action_delete_related_moves()
        if self.company_id.pdc_operation_type == 'cancel':
            self.write({'state': 'cancel'})

        elif self.company_id.pdc_operation_type == 'cancel_draft':
            self.write({'state': 'draft'})

        elif self.company_id.pdc_operation_type == 'cancel_delete':
            self.write({'state': 'draft'})
            self.unlink()
            return {'type': 'ir.actions.act_window_close'}

    def action_delete_related_moves(self):

        for model in self:
            move_ids = self.env['account.move'].search(
                [('pdc_id', '=', model.id)])
            for move in move_ids:
                move.button_cancel()
                move.button_draft()
                move.unlink()

    def action_set_draft(self):
        self.check_payment_amount()
        self.write({'state': 'draft'})

    def action_done(self):
        self._check_pdc_admin()

        if not self.done_date:
            self.write({
                'done_date': fields.Datetime.now().astimezone(timezone('Asia/Dubai' or "UTC")),
            })

        move = self.env['account.move']

        self.check_payment_amount()  # amount must be positive
        pdc_account = self.check_pdc_account()
        bank_account = self.journal_id.default_account_id.id

        # Create Journal Item
        move_line_vals_debit = {}
        move_line_vals_credit = {}
        if self.payment_type == 'receive_money':
            move_line_vals_debit = self.get_debit_move_line(bank_account)
            move_line_vals_credit = self.get_credit_move_line(pdc_account)
        else:
            move_line_vals_debit = self.get_debit_move_line(pdc_account)
            move_line_vals_credit = self.get_credit_move_line(bank_account)

        if self.memo:
            move_line_vals_debit.update(
                {'name': 'PDC Payment :' + self.memo, 'partner_id': self.partner_id and self.partner_id.id})
            move_line_vals_credit.update(
                {'name': 'PDC Payment :' + self.memo, 'partner_id': self.partner_id and self.partner_id.id})
        else:
            move_line_vals_debit.update(
                {'name': 'PDC Payment', 'partner_id': self.partner_id and self.partner_id.id})
            move_line_vals_credit.update(
                {'name': 'PDC Payment', 'partner_id': self.partner_id and self.partner_id.id})

        # create move and post it
        move_vals = self.get_move_vals(
            move_line_vals_debit, move_line_vals_credit)

        if self.invoice_ids:

            move_id = move.create(move_vals)
            move_id.action_post()

            payment_lines = move_id.line_ids.filtered(
                lambda l: l.account_id.reconcile
            )

            payment_amount = self.payment_amount

            for invoice in self.invoice_ids:

                if payment_amount <= 0:
                    break

                invoice_lines = invoice.line_ids.filtered(
                    lambda l: l.account_id.reconcile and not l.reconciled
                )

                if not invoice_lines:
                    continue

                lines_to_reconcile = invoice_lines + payment_lines

                # ✅ Odoo official reconciliation
                lines_to_reconcile.reconcile()

                payment_amount -= invoice.amount_residual

        else:
            move_id = move.create(move_vals)
            move_id.action_post()

        self.write({
            'state': 'done',
        })

        self.reset_account_pdc_config_partner()

    # multi action methods
    def action_pdc_cancel(self):
        self._check_pdc_admin()

        self.action_delete_related_moves()
        self.write({'state': 'cancel'})

    def action_pdc_cancel_draft(self):
        self._check_pdc_admin()

        self.action_delete_related_moves()
        self.write({'state': 'draft'})

    def action_pdc_cancel_delete(self):
        self._check_pdc_admin()

        self.action_delete_related_moves()
        self.write({'state': 'draft'})
        self.unlink()

    # ==============================
    #    CRON SCHEDULER CUSTOMER
    # ==============================
    @api.model
    def notify_customer_due_date(self):
        emails = []
        if self.env.company.is_cust_due_notify:
            notify_day_1 = self.env.company.notify_on_1
            notify_day_2 = self.env.company.notify_on_2
            notify_day_3 = self.env.company.notify_on_3
            notify_day_4 = self.env.company.notify_on_4
            notify_day_5 = self.env.company.notify_on_5
            notify_date_1 = False
            notify_date_2 = False
            notify_date_3 = False
            notify_date_4 = False
            notify_date_5 = False
            if notify_day_1:
                notify_date_1 = fields.date.today() + timedelta(days=int(notify_day_1) * -1)
            if notify_day_2:
                notify_date_2 = fields.date.today() + timedelta(days=int(notify_day_2) * -1)
            if notify_day_3:
                notify_date_3 = fields.date.today() + timedelta(days=int(notify_day_3) * -1)
            if notify_day_4:
                notify_date_4 = fields.date.today() + timedelta(days=int(notify_day_4) * -1)
            if notify_day_5:
                notify_date_5 = fields.date.today() + timedelta(days=int(notify_day_5) * -1)

            records = self.search([('payment_type', '=', 'receive_money')])
            for user in self.env.company.sh_user_ids:
                if user.partner_id and user.partner_id.email:
                    emails.append(user.partner_id.email)
            email_values = {
                'email_to': ','.join(emails),
            }
            view = self.env.ref("sh_pdc.sh_pdc_payment_form_view",
                                raise_if_not_found=False).sudo()
            view_id = view.id if view else 0
            for record in records:
                if (record.due_date == notify_date_1
                        or record.due_date == notify_date_2
                        or record.due_date == notify_date_3
                        or record.due_date == notify_date_4
                        or record.due_date == notify_date_5):

                    if self.env.company.is_notify_to_customer:
                        template_download_id = self.env.ref(
                            'sh_pdc.sh_pdc_company_to_customer_notification_1')
                        _ = record.env['mail.template'].browse(
                            template_download_id.id
                        ).send_mail(record.id, email_layout_xmlid='mail.mail_notification_light', force_send=True)
                    if self.env.company.is_notify_to_user and self.env.company.sh_user_ids:
                        url = ''
                        base_url = request.env['ir.config_parameter'].sudo(
                        ).get_param('web.base.url')
                        url = base_url + "/web#id=" + \
                              str(record.id) + \
                              "&&model=pdc.wizard&view_type=form&view_id=" + \
                              str(view_id)
                        ctx = {
                            "customer_url": url,
                        }
                        # template_download_id = record.env['ir.model.data'].get_object(
                        #     'sh_pdc', 'sh_pdc_company_to_int_user_notification_1'
                        #     )
                        template_download_id = self.env.ref(
                            'sh_pdc.sh_pdc_company_to_int_user_notification_1')
                        _ = request.env['mail.template'].sudo().browse(template_download_id.id).with_context(
                            ctx).send_mail(
                            record.id, email_values=email_values, email_layout_xmlid='mail.mail_notification_light',
                            force_send=True)

    def action_server_cancel(self):
        self._check_pdc_admin()

        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')

        if len(active_ids) > 0:
            active_models = self.env[active_model].browse(active_ids)
            for rec in active_models:
                rec.action_delete_related_moves()
                if self.company_id.pdc_operation_type == 'cancel':
                    rec.write({'state': 'cancel'})

                elif self.company_id.pdc_operation_type == 'cancel_draft':
                    rec.write({'state': 'draft'})

                elif self.company_id.pdc_operation_type == 'cancel_delete':
                    rec.write({'state': 'draft'})
                    rec.unlink()

    def reset_account_pdc_config_partner(self):
        for rec in self:
            move_line_ids = self.env['account.move.line'].search([('pdc_id', '=', rec.id), ('move_type', '=', 'entry')])
            move_line_ids.filtered(lambda line: line.account_id.id in (self.env.company.pdc_customer.id,
                                                                       self.env.company.pdc_vendor.id)).partner_id = False

    def reset_all_account_pdc_config_partner(self):
        journal_entries = self.env['account.move'].search(
            [('move_type', '=', 'entry'), ('state', '=', 'posted'), ('pdc_id', '!=', False)])
        print(len(journal_entries))
        journal_entries_ids = journal_entries.ids
        journal_entries.button_draft()
        self.search([]).reset_account_pdc_config_partner()
