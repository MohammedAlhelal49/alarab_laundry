from odoo import api, fields, models


class PartnerPropertySet(models.Model):
    _name = "res.partner.property.set"
    _description = "Contact Property Set"

    name = fields.Char(
        string="Name",
        required=True,
        default="Contact Properties",
    )

    properties_definition = fields.PropertiesDefinition(
        string="Contact Properties",
    )


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "properties.print.mixin"]

    @api.model
    def _default_property_set_id(self):
        property_set = self.env["res.partner.property.set"].search([], limit=1)

        if not property_set:
            property_set = self.env["res.partner.property.set"].create({
                "name": "Contact Properties",
            })

        return property_set.id

    property_set_id = fields.Many2one(
        "res.partner.property.set",
        string="Property Set",
        default=_default_property_set_id,
        copy=False,
    )

    custom_properties = fields.Properties(
        string="Properties",
        definition="property_set_id.properties_definition",
        copy=True,
    )