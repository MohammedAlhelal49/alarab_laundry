from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountInvoiceDiscount(models.TransientModel):
    _name = 'account.invoice.discount'
    _description = 'Invoice/Bill Discount Wizard'

    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Invoice/Bill',
        required=True,
        readonly=True,
    )
    discount_type = fields.Selection(
        selection=[
            ('aml_discount', 'On All Order Lines'),
            ('global_discount', 'Global Discount'),
            ('fixed_amount', 'Fixed Amount'),
        ],
        string='Discount Type',
        default='aml_discount',
        required=True,
    )
    discount_percentage = fields.Float(
        string='Discount',
        digits='Discount',
    )
    discount_amount = fields.Float(
        string='Discount Amount',
        digits='Account',
    )

    # -------------------------------------------------------------------------
    # ONCHANGE
    # -------------------------------------------------------------------------

    @api.onchange('discount_type')
    def _onchange_discount_type(self):
        self.discount_percentage = 0.0
        self.discount_amount = 0.0

    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------

    def _validate(self):
        self.ensure_one()
        if self.discount_type in ('aml_discount', 'global_discount'):
            if not (0.0 <= self.discount_percentage <= 100.0):
                raise UserError(_('Discount percentage must be between 0 and 100.'))
        else:
            if self.discount_amount <= 0.0:
                raise UserError(_('Discount amount must be greater than zero.'))

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _get_product_lines(self):
        """Return only product lines (exclude sections, notes, tax lines, etc.)."""
        return self.move_id.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product'
        )

    def _get_or_create_discount_product(self):
        """Get or create the discount product for the company."""
        company = self.move_id.company_id
        product = company.invoice_discount_product_id
        if not product:
            product = self.env.ref(
                'dekad_account_enhancement.product_invoice_discount',
                raise_if_not_found=False,
            )
            if product:
                company.invoice_discount_product_id = product
        if not product:
            product = self.env['product.product'].create({
                'name': _('Discount'),
                'type': 'service',
                'active': False,
            })
            company.invoice_discount_product_id = product
        return product

    def _get_discount_account(self, product):
        """
        Return the correct account for the discount line depending on move type.
        - Customer Invoice  (out_invoice) -> income account
        - Vendor Bill       (in_invoice)  -> expense account
        """
        move = self.move_id
        accounts = product.product_tmpl_id.get_product_accounts(
            fiscal_pos=move.fiscal_position_id,
        )
        if move.is_purchase_document(include_receipts=True):
            account = accounts.get('expense')
        else:
            account = accounts.get('income')

        # Fallback: use the first product line's account
        if not account:
            product_lines = self._get_product_lines()
            account = product_lines[:1].account_id

        return account

    # -------------------------------------------------------------------------
    # APPLY METHODS
    # -------------------------------------------------------------------------

    def _apply_aml_discount(self):
        """Write discount% directly on every product line."""
        lines = self._get_product_lines()
        if not lines:
            raise UserError(_('No product lines found on this invoice.'))
        lines.write({'discount': self.discount_percentage})

    def _apply_global_discount(self):
        """
        Add a single negative product line for the discount.
        No taxes are applied -- the discount affects the full amount (subtotal + tax).
        Line is placed last via sequence=999.
        """
        move = self.move_id
        product_lines = self._get_product_lines()
        if not product_lines:
            raise UserError(_('No product lines found on this invoice.'))

        discount_product = self._get_or_create_discount_product()
        discount_account = self._get_discount_account(discount_product)

        total_subtotal = sum(product_lines.mapped('price_subtotal'))
        discount_amount = total_subtotal * (self.discount_percentage / 100.0)

        if not discount_amount:
            return

        self.env['account.move.line'].create({
            'move_id': move.id,
            'product_id': discount_product.id,
            'name': _('Discount %s%%') % self.discount_percentage,
            'account_id': discount_account.id,
            'price_unit': -discount_amount,
            'quantity': 1.0,
            'tax_ids': [(5, 0, 0)],
            'display_type': 'product',
            'sequence': 999,
        })

    def _apply_fixed_amount(self):
        """
        Add a single negative line with the fixed discount amount.
        No taxes applied -- discount is on the full total.
        Line is placed last via sequence=999.
        """
        move = self.move_id
        product_lines = self._get_product_lines()
        if not product_lines:
            raise UserError(_('No product lines found on this invoice.'))

        discount_product = self._get_or_create_discount_product()
        discount_account = self._get_discount_account(discount_product)

        self.env['account.move.line'].create({
            'move_id': move.id,
            'product_id': discount_product.id,
            'name': _('Discount'),
            'account_id': discount_account.id,
            'price_unit': -self.discount_amount,
            'quantity': 1.0,
            'tax_ids': [(5, 0, 0)],
            'display_type': 'product',
            'sequence': 999,
        })

    # -------------------------------------------------------------------------
    # MAIN ACTION
    # -------------------------------------------------------------------------

    def action_apply_discount(self):
        self.ensure_one()
        self._validate()

        move = self.move_id
        if move.state != 'draft':
            raise UserError(_('You can only apply a discount on a draft invoice or bill.'))

        if self.discount_type == 'aml_discount':
            self._apply_aml_discount()
        elif self.discount_type == 'global_discount':
            self._apply_global_discount()
        elif self.discount_type == 'fixed_amount':
            self._apply_fixed_amount()

        return {'type': 'ir.actions.act_window_close'}
