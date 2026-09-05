from odoo import api, fields, models


class SaleOrderPropertySet(models.Model):
    _name = "sale.order.property.set"
    _description = "Sale Order Property Set"

    name = fields.Char(
        string="Name",
        required=True,
        default="Sale Order Properties",
    )

    properties_definition = fields.PropertiesDefinition(
        string="Sale Order Properties",
    )


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "properties.print.mixin"]

    @api.model
    def _default_property_set_id(self):
        property_set = self.env["sale.order.property.set"].search([], limit=1)

        if not property_set:
            property_set = self.env["sale.order.property.set"].create({
                "name": "Sale Order Properties",
            })

        return property_set.id

    property_set_id = fields.Many2one(
        "sale.order.property.set",
        string="Property Set",
        default=_default_property_set_id,
        copy=False,
    )

    custom_properties = fields.Properties(
        string="Properties",
        definition="property_set_id.properties_definition",
        copy=True,
    )