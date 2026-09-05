from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    subject = fields.Char(string="Subject")
    engagement_type = fields.Char(
        string="Engagement Type",
        compute='_compute_engagement_type',
        store=True,
    )

    @api.depends('order_line.product_id.categ_id')
    def _compute_engagement_type(self):
        for order in self:
            categories = order.order_line.filtered(
                lambda l: not l.display_type
            ).mapped('product_id.categ_id.name')
            order.engagement_type = categories[0] if categories else False

    reference_code = fields.Char(
        string="Reference Code",
        compute='_compute_reference_code',
        store=True,
    )

    @api.depends('order_line.product_id.categ_id.code', 'date_order')
    def _compute_reference_code(self):
        for order in self:
            lines = order.order_line.filtered(lambda l: not l.display_type)
            category_code = lines[:1].product_id.categ_id.code or 'GEN'
            date_str = order.date_order.strftime('%Y%m%d') if order.date_order else ''
            order.reference_code = f"{category_code}-{date_str}"