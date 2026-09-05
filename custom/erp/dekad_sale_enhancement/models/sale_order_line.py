from odoo import api, fields, models, _
from odoo import models, fields, api
from decimal import Decimal
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError

VAT_RATE = Decimal('0.05')  # UAE 5% VAT


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    amount_delivered = fields.Float(
        string='Qty Delivered Amount', digits='Amount Delivered',
        compute="_compute_amount_delivered", readonly=True, store=True)

    amount_to_deliver = fields.Float(compute='_compute_amount_to_deliver', string='Qty To Deliver Amount', store=True,
                                     readonly=True,
                                     digits='Amount to deliver')


    line_index = fields.Integer(string='Line #', compute='_compute_line_index', store=False)

    @api.depends('order_id.order_line')
    def _compute_line_index(self):
        for order in self.mapped('order_id'):
            for idx, line in enumerate(order.order_line.sorted('sequence'), start=1):
                line.line_index = idx


    @api.depends('qty_delivered', 'price_unit')
    def _compute_amount_delivered(self):
        for rec in self:
            rec.amount_delivered = rec.qty_delivered * rec.price_unit

    @api.depends('qty_to_deliver', 'price_unit')
    def _compute_amount_to_deliver(self):
        for rec in self:
            rec.amount_to_deliver = rec.qty_to_deliver * rec.price_unit

    price_unit_vat = fields.Monetary(
        string="Unit Price (incl. VAT)",
        compute="_compute_price_unit_vat",
        store=False,
        currency_field="currency_id",
        help="Unit price including VAT. Editing this field updates the Unit Price (excl. VAT).",
    )
    #
    # ------------------------------
    # Compute price_unit_vat dynamically from price_unit
    # ------------------------------
    @api.depends("price_unit", "tax_id")
    def _compute_price_unit_vat(self):
        for line in self:
            price_ex = line.price_unit or 0.0

            if not line.tax_id:
                line.price_unit_vat = price_ex
                continue

            taxes = line.tax_id.compute_all(
                price_ex,
                currency=line.order_id.currency_id,
                quantity=1,
                product=line.product_id,
                partner=line.order_id.partner_id,
            )

            line.price_unit_vat = taxes["total_included"]

    @api.onchange("price_unit_vat", "tax_id")
    def _onchange_price_unit_vat(self):
        for line in self:
            values = set(line.tax_id.mapped('price_include_override'))
            tax_type = False
            has_included = 'tax_included' in values
            has_excluded = False in values or 'tax_excluded' in values

            if has_included and has_excluded:
                tax_type = "mix"
            elif has_included:
                tax_type = "tax_included"
            else:
                tax_type = "tax_excluded"
            print(tax_type)

            if not line.price_unit_vat:
                line.price_unit = 0.0
                continue

            if not line.tax_id:
                line.price_unit = line.price_unit_vat
                continue

            currency = line.order_id.currency_id

            # Use tax engine in reverse mode
            taxes = line.tax_id.with_context(force_price_include=True).compute_all(
                line.price_unit_vat,
                currency=currency,
                quantity=1,
                product=line.product_id,
                partner=line.order_id.partner_id,
            )

            if tax_type == "mix":
               line.price_unit_vat = line.price_unit

               return {
                    'warning': {
                        'title': _('Mixed Taxes Detected'),
                        'message': _(
                            'Since You are using both Included and Excluded taxes on the same line.\n'
                            'You can only input the price from the price unit field'
                        )
                    }
                }

            price_ex = taxes["total_excluded"]
            price_in = taxes["total_included"]

            line.price_unit = currency.round(price_in if tax_type =="tax_included" else price_ex )

