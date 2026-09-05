# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    attendance_geofence_enabled = fields.Boolean(
        string='Geofence Enforcement',
        default=False,
        help='When enabled, employees with assigned geofence zones must be physically '
             'inside a zone to check-in or check-out. GPS coordinates are validated '
             'server-side using the Haversine formula.',
    )
