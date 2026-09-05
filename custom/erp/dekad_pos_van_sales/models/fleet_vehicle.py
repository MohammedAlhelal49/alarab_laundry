from odoo import models, fields, api

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    is_van_sale = fields.Boolean(
        string="Is Van Sale",
        help="If checked, restrict driver selection to contacts linked to users."
    )
