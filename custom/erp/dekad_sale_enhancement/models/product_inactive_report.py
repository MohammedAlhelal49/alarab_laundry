from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    never_sold = fields.Boolean(
        string="Never Sold",
        compute="_compute_never_sold",
        store=True,
    )

    @api.depends('product_variant_ids')
    def _compute_never_sold(self):
        SaleOrderLine = self.env['sale.order.line']
        for product in self:
            sold = SaleOrderLine.search_count([
                ('product_id', 'in', product.product_variant_ids.ids)
            ]) > 0
            product.never_sold = not sold


class ProductProduct(models.Model):
    _inherit = "product.product"

    sale_order_line_ids = fields.One2many(
        'sale.order.line',
        'product_id',
        string="Sale Order Lines"
    )

    default_code_name = fields.Char(
        string="Reference and Name",
        compute="_compute_default_code_name",
        store=True
    )

    def _compute_default_code_name(self):
        for rec in self:
            code = f"[{rec.default_code}]" if rec.default_code else ""
            rec.default_code_name = f"{code} {rec.name}".strip()