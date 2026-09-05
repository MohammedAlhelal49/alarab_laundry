from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    duplicate_contact_policy = fields.Selection(
        related='company_id.duplicate_contact_policy',
        readonly=False,
        string='Duplicate Phone/Mobile Policy',
    )
