from odoo import api, fields, models


class HrExpensePropertySet(models.Model):
    _name = "hr.expense.property.set"
    _description = "Expense Property Set"

    name = fields.Char(
        string="Name",
        required=True,
        default="Expense Properties",
    )

    properties_definition = fields.PropertiesDefinition(
        string="Expense Properties",
    )


class HrExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["hr.expense", "properties.print.mixin"]

    @api.model
    def _default_property_set_id(self):
        property_set = self.env["hr.expense.property.set"].search([], limit=1)

        if not property_set:
            property_set = self.env["hr.expense.property.set"].create({
                "name": "Expense Properties",
            })

        return property_set.id

    property_set_id = fields.Many2one(
        "hr.expense.property.set",
        string="Property Set",
        default=_default_property_set_id,
        copy=False,
    )

    custom_properties = fields.Properties(
        string="Properties",
        definition="property_set_id.properties_definition",
        copy=True,
    )