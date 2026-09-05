# -*- coding: utf-8 -*-
# © 2025 ehuerta _at_ ixer.mx
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    min_price = fields.Float(string='Minimum Sale Price')
    max_price = fields.Float(string='Maximum Sale Price')
    is_additional_charge = fields.Boolean(
        string="Additional Charge Product",
        help="This product will be used when applying an additional charge in POS.",
    )

    @api.constrains('min_price', 'max_price')
    def _check_price_limits(self):
        for rec in self:
            # Prevent negative prices
            if rec.min_price < 0 or rec.max_price < 0:
                raise ValidationError("Minimum and Maximum prices must be zero or positive.")
            # Prevent illogical price range
            if rec.min_price and rec.max_price and rec.min_price > rec.max_price:
                raise ValidationError("Minimum price cannot be greater than maximum price.")


    multi_uom_price_ids = fields.One2many('product.tmpl.multi.uom.price', 'product_tmpl_id', string='UOM Prices')

    @api.constrains('multi_uom_price_ids')
    def validate_multi_uom_price_ids(self):
        for product in self:
            if product.multi_uom_price_ids and not product.multi_uom_price_ids.filtered(
                    lambda rec: rec.uom_id.uom_type == 'reference'):
                raise UserError(_(f'Point of sale uom items must have the default uom for the product {product.name}'))

    def write(self, vals):
        res = super().write(vals)
        if 'multi_uom_price_ids' in vals:
            for rec in self:
                commands = [(5, 0, 0)]
                for line in rec.multi_uom_price_ids:
                    commands.append((0, 0, {
                        'uom_id': line.uom_id.id,
                    }))
                assigned_product = rec.product_variant_ids.filtered(
                    lambda data_rec: not data_rec.product_template_attribute_value_ids)
                assigned_product.multi_uom_price_ids = commands

        return res


class ProductProduct(models.Model):
    _inherit = "product.product"

    min_price = fields.Float(
        string="Minimum Sale Price",
        store=True,
        readonly=False,
    )
    max_price = fields.Float(
        string="Maximum Sale Price",
        store=True,
        readonly=False,
    )

    multi_uom_price_ids = fields.One2many(
        "product.multi.uom.price",
        "product_id",
        string="UOM Prices",
    )

    def _load_pos_data_fields(self, config_id):
        """
        إضافة حقل qty_available إلى البيانات
        المرسلة إلى POS session عند التحميل
        """
        fields = super()._load_pos_data_fields(config_id)
        if "qty_available" not in fields:
            fields.append("qty_available")
        return fields


    @api.constrains("multi_uom_price_ids")
    def validate_multi_uom_price_ids(self):
        for product in self:
            if (
                product.multi_uom_price_ids
                and not product.multi_uom_price_ids.filtered(
                    lambda rec: rec.uom_id.uom_type == "reference"
                )
            ):
                raise UserError(
                    _(
                        "Point of sale UOM items must have the default UOM for the product %s"
                    )
                    % product.name
                )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)

        extra_fields = [
            "min_price",
            "max_price",
            "x_name_ar",
            "x_name_en",
            "display_name",
            "product_template_attribute_value_ids",
        ]

        for field in extra_fields:
            if field not in fields:
                fields.append(field)

        return fields

    @api.model
    def _load_pos_data(self, data):
        result = super()._load_pos_data(data)

        if result and "data" in result:
            for product_data in result["data"]:
                product = self.browse(product_data.get("id"))
                if product.exists():
                    variant_values = product.product_template_attribute_value_ids.mapped(
                        "name"
                    )
                    product_data["variant_name"] = (
                        ", ".join(variant_values) if variant_values else ""
                    )
                    product_data["display_name"] = product.display_name

        return result

