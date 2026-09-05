from odoo import fields, models


class PropertyUsage(models.Model):
    _name = "property.usage"
    _description = "Property Usage"

    name = fields.Char(
        string="استخدام العقار",
        required=True,
        translate=True,
    )


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    property_reference = fields.Char(
        string="رقم تعريف العقار"
    )

    unit_reference = fields.Char(
        string="رقم تعريف الوحدة"
    )

    property_code = fields.Char(
        string="الرمز العقاري"
    )

    basin = fields.Char(
        string="الحوض"
    )

    plot_no = fields.Char(
        string="القطعة"
    )

    property_usage_id = fields.Many2one(
        "property.usage",
        string="استخدام العقار",
    )