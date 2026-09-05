from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrderDiscount(models.TransientModel):
    """Wizard that applies a discount to a Purchase Order.

    Three modes:

    sol_discount  - Writes discount (%) directly on every existing PO line.
    po_discount   - Creates a single negative-price service line (global %).
    amount        - Creates a single negative-price service line (fixed amount).

    No taxes are applied on the discount line in all modes -- the discount
    affects the full total (subtotal + tax).
    """

    _name = 'purchase.order.discount'
    _description = "Purchase Order Discount Wizard"

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    purchase_order_id = fields.Many2one(
        comodel_name='purchase.order',
        string="Purchase Order",
        default=lambda self: self.env.context.get('active_id'),
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(related='purchase_order_id.company_id')
    currency_id = fields.Many2one(related='purchase_order_id.currency_id')

    discount_type = fields.Selection(
        selection=[
            ('sol_discount', "On All Order Lines"),
            ('po_discount',  "Global Discount"),
            ('amount',       "Fixed Amount"),
        ],
        string="Discount Type",
        default='sol_discount',
        required=True,
    )

    # Stored as fraction (0.0 - 1.0) because widget="percentage" multiplies by 100 for display.
    # e.g. user types "10" -> stored as 0.10
    discount_percentage = fields.Float(
        string="Percentage",
        help="Discount percentage (e.g. enter 10 for 10 %).",
    )

    discount_amount = fields.Monetary(
        string="Amount",
        help="Fixed discount amount deducted from the PO total.",
    )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    @api.constrains('discount_type', 'discount_percentage')
    def _check_discount_percentage(self):
        for wizard in self:
            if (
                wizard.discount_type in ('sol_discount', 'po_discount')
                and wizard.discount_percentage > 1.0
            ):
                raise ValidationError(_("Invalid discount amount"))

    @api.constrains('discount_type', 'discount_amount')
    def _check_discount_amount(self):
        for wizard in self:
            if wizard.discount_type == 'amount' and wizard.discount_amount < 0:
                raise ValidationError(_("Discount amount must be a positive value."))

    # ------------------------------------------------------------------
    # Discount product helpers
    # ------------------------------------------------------------------

    def _prepare_discount_product_values(self):
        self.ensure_one()
        return {
            'name': _('Discount'),
            'type': 'service',
            'invoice_policy': 'order',
            'list_price': 0.0,
            'company_id': self.company_id.id,
            'taxes_id': False,
            'supplier_taxes_id': False,
            'purchase_ok': True,
            'sale_ok': False,
        }

    def _get_discount_product(self):
        """Return the product.product for the discount line, creating it if needed."""
        self.ensure_one()
        discount_product = self.company_id.purchase_discount_product_id
        if not discount_product:
            if (
                self.env['product.product'].has_access('create')
                and self.company_id.has_access('write')
                and self.company_id._filtered_access('write')
                and self.company_id.check_field_access_rights(
                    'write', ['purchase_discount_product_id']
                )
            ):
                self.company_id.purchase_discount_product_id = (
                    self.env['product.product'].create(
                        self._prepare_discount_product_values()
                    )
                )
            else:
                raise ValidationError(_(
                    "No discount product is configured for this company yet.\n"
                    "You can either use 'On All Order Lines' mode, or ask an "
                    "administrator to configure one under:\n"
                    "Purchase -> Configuration -> Settings -> Pricing."
                ))
            discount_product = self.company_id.purchase_discount_product_id
        return discount_product

    # ------------------------------------------------------------------
    # Line values builder
    # ------------------------------------------------------------------

    def _prepare_discount_line_values(self, product, amount, description=None):
        """Build vals for a new purchase.order.line discount entry.

        ``amount`` must be positive; the negative sign is applied here.
        No taxes are set -- discount applies on the full total (subtotal + tax).
        sequence=999 ensures the line is always last.
        """
        self.ensure_one()
        return {
            'order_id': self.purchase_order_id.id,
            'product_id': product.id,
            'name': description or _('Discount'),
            'product_qty': 1.0,
            'product_uom': product.uom_po_id.id or product.uom_id.id,
            'price_unit': -abs(amount),
            'taxes_id': [Command.set([])],
            'sequence': 999,
            'date_planned': (
                self.purchase_order_id.date_planned
                or fields.Datetime.now()
            ),
        }

    # ------------------------------------------------------------------
    # Core: create discount lines
    # ------------------------------------------------------------------

    def _create_discount_lines(self):
        """Create a single purchase.order.line for global/fixed discounts.

        discount_percentage is stored as a fraction (0.0-1.0) by widget="percentage".
        e.g. user types "10" -> stored 0.10 -> display shows "10 %"
        """
        self.ensure_one()
        discount_product = self._get_discount_product()

        if self.discount_type == 'amount':
            # Fixed Amount: single line with the given monetary amount
            vals_list = [
                self._prepare_discount_line_values(
                    product=discount_product,
                    amount=self.discount_amount,
                )
            ]

        else:
            # Global Discount (po_discount): compute total subtotal across all lines
            total_subtotal = 0.0
            for line in self.purchase_order_id.order_line:
                if line.display_type:
                    continue
                if not line.product_qty or not line.price_unit:
                    continue
                total_subtotal += (
                    line.price_unit
                    * line.product_qty
                    * (1.0 - (line.discount or 0.0) / 100.0)
                )

            if not total_subtotal:
                return self.env['purchase.order.line']

            pct_fraction = self.discount_percentage          # e.g. 0.10
            pct_display  = self.discount_percentage * 100.0  # e.g. 10.0

            vals_list = [
                self._prepare_discount_line_values(
                    product=discount_product,
                    amount=total_subtotal * pct_fraction,
                    description=_(
                        "Discount %(percent)g%%",
                        percent=pct_display,
                    ),
                )
            ]

        return self.env['purchase.order.line'].create(vals_list)

    # ------------------------------------------------------------------
    # Main action
    # ------------------------------------------------------------------

    def action_apply_discount(self):
        """Apply the configured discount to the linked Purchase Order."""
        self.ensure_one()
        self = self.with_company(self.company_id)

        if self.discount_type == 'sol_discount':
            # On All Order Lines:
            # discount_percentage stored as fraction (0.0-1.0),
            # purchase.order.line.discount stores 0-100, so multiply by 100.
            lines = self.purchase_order_id.order_line.filtered(
                lambda l: not l.display_type and not l.is_downpayment
            )
            lines.write({'discount': self.discount_percentage * 100.0})
        else:
            self._create_discount_lines()
