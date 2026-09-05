# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_geofence_enabled = fields.Boolean(
        related='company_id.attendance_geofence_enabled',
        readonly=False,
    )
