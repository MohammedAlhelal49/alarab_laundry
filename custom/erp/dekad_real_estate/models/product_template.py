from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    min_sale_price = fields.Float(string="Minimum Price", default=0.0)
    max_sale_price = fields.Float(string="Maximum Price", default=0.0)

    show_price_limit_fields = fields.Boolean(
        compute="_compute_show_price_limit_fields",
        store=False
    )

    def _compute_show_price_limit_fields(self):
        for rec in self:
            rec.show_price_limit_fields = rec.env.company.enforce_product_price_limits


    @api.constrains('list_price', 'min_sale_price', 'max_sale_price')
    def _check_list_price_bounds(self):
        for rec in self:
            if not rec.env.company.enforce_product_price_limits:
                continue

            if rec.min_sale_price and rec.list_price < rec.min_sale_price:
                raise ValidationError(
                    f"List Price ({rec.list_price}) is below the minimum allowed ({rec.min_sale_price})."
                )
            if rec.max_sale_price and rec.list_price > rec.max_sale_price:
                raise ValidationError(
                    f"List Price ({rec.list_price}) is above the maximum allowed ({rec.max_sale_price})."
                )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    min_sale_price = fields.Float(related='product_tmpl_id.min_sale_price', readonly=False)
    max_sale_price = fields.Float(related='product_tmpl_id.max_sale_price', readonly=False)



