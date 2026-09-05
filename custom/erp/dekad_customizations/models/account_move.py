from odoo import api, fields, models


class AccountMovePropertySet(models.Model):
    _name = "account.move.property.set"
    _description = "Journal Entry Property Set"

    name = fields.Char(
        string="Name",
        required=True,
        default="Accounting Properties",
    )

    properties_definition = fields.PropertiesDefinition(
        string="Accounting Properties",
    )


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "properties.print.mixin"]

    @api.model
    def _default_property_set_id(self):
        property_set = self.env["account.move.property.set"].search([], limit=1)

        if not property_set:
            property_set = self.env["account.move.property.set"].create({
                "name": "Accounting Properties",
            })

        return property_set.id

    property_set_id = fields.Many2one(
        "account.move.property.set",
        string="Property Set",
        default=_default_property_set_id,
        copy=False,
    )

    custom_properties = fields.Properties(
        string="Properties",
        definition="property_set_id.properties_definition",
        copy=True,
    )