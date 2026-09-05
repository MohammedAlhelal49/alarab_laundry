from odoo import models, fields, api
from odoo.osv import expression


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    

    from_history = fields.Boolean(
        string="From Price History",
        readonly=True,
        help="Checked if the price was fetched from customer price history"
    )

    use_price_from_history = fields.Boolean(
        string="Use Price from History",
        default=True,
        help="If enabled, the selling price will be fetched from customer price history when available."
    )

    unit_cost = fields.Float(
        string="Unit Cost",
        compute="_compute_unit_cost",
        store=True,
        readonly=True,
        help="Pulled from product's standard cost (internal only)."
    )

    @api.depends('product_id', 'product_id.standard_price')
    def _compute_unit_cost(self):
        for line in self:
            if line.product_id:
                line.unit_cost = line.product_id.standard_price
            else:
                line.unit_cost = 0.0

    @api.onchange('product_id', 'use_price_from_history')
    def _onchange_product_id_fetch_customer_price_history(self):
        print('changed')
        for line in self:

            # Only apply on quotations
            if not line.order_id or line.order_id.state != 'draft':
                return

            # User explicitly chose manual pricing
            if not line.use_price_from_history:
                return

            if not line.product_id or not line.order_id.partner_id:
                return

            customer = line.order_id.partner_id
            if not customer:
                return

            history = self.env['sale.customer.price.history'].sudo().search([
                ('partner_id', '=', customer.id),
                ('product_id', '=', line.product_id.id),

            ], order='date desc', limit=1)
            print(history)

            if history:
                line.price_unit = history.price_unit