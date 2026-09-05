from odoo import api, fields, models


class PurchaseOrderPropertySet(models.Model):
    _name = "purchase.order.property.set"
    _description = "Purchase Order Property Set"

    name = fields.Char(
        string="Name",
        required=True,
        default="Purchase Order Properties",
    )

    properties_definition = fields.PropertiesDefinition(
        string="Purchase Order Properties",
    )


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "properties.print.mixin"]

    @api.model
    def _default_property_set_id(self):
        property_set = self.env["purchase.order.property.set"].search([], limit=1)

        if not property_set:
            property_set = self.env["purchase.order.property.set"].create({
                "name": "Purchase Order Properties",
            })

        return property_set.id

    property_set_id = fields.Many2one(
        "purchase.order.property.set",
        string="Property Set",
        default=_default_property_set_id,
        copy=False,
    )

    custom_properties = fields.Properties(
        string="Properties",
        definition="property_set_id.properties_definition",
        copy=True,
    )