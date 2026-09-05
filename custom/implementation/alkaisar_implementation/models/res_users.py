from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    # The new field on the User profile
    default_payment_journal_id = fields.Many2one(
        'account.journal',
        string='Default Payment Journal',
        help="This journal will be selected by default when this user creates a payment."
    )

