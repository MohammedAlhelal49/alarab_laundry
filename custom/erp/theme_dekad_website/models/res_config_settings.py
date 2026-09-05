from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    website_lead_activity_user_ids = fields.Many2many(
        related='company_id.website_lead_activity_user_ids',
        readonly=False,
        string='Website Lead Activity Recipients'
    )