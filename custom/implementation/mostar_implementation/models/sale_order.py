from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_salutation = fields.Selection(
        related='partner_id.custom_salutation',
        string="Contact Salutation",
        readonly=False
    )

    purchase_order_ids = fields.One2many(
        'purchase.order',
        'related_sale_order_id',
        string='Linked Purchase Orders'
    )

    purchase_order_amount = fields.Monetary(
        string='Purchase Order Amount',
        compute='_compute_purchase_order_amount',
        currency_field='currency_id',
        store=True
    )

    margin = fields.Monetary(
        string='Margin',
        compute='_compute_margin',
        currency_field='currency_id',
        store=True
    )

    @api.depends('purchase_order_ids.amount_total')
    def _compute_purchase_order_amount(self):
        for order in self:
            order.purchase_order_amount = sum(order.purchase_order_ids.mapped('amount_total'))

    @api.depends('amount_total', 'purchase_order_amount')
    def _compute_margin(self):
        for order in self:
            order.margin = order.amount_total - order.purchase_order_amount

