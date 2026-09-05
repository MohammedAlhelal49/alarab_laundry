from odoo import fields, models


class RealEstateBuildings(models.Model):
    _inherit = "real.estate.buildings"

    municipality = fields.Char(
        string="البلدية"
    )

    area = fields.Char(
        string="المنطقة"
    )