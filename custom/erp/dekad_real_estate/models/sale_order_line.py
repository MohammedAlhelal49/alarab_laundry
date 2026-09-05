from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.constrains('price_unit', 'product_id')
    def _check_price_within_bounds(self):
        for line in self:
            if not line.env.company.enforce_product_price_limits:
                continue

            product = line.product_id.product_tmpl_id
            if product.min_sale_price and line.price_unit < product.min_sale_price:
                raise ValidationError(
                    f"Price {line.price_unit} is below the minimum allowed ({product.min_sale_price}) for product {product.name}."
                )
            if product.max_sale_price and line.price_unit > product.max_sale_price:
                raise ValidationError(
                    f"Price {line.price_unit} is above the maximum allowed ({product.max_sale_price}) for product {product.name}."
                )
