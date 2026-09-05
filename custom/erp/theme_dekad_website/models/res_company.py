from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    website_lead_activity_user_ids = fields.Many2many(
        'res.users',
        string='Website Lead Activity Recipients',
        help='Users who will receive a To-Do activity when a new demo or consultation is requested.'
    )