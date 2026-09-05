from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    duplicate_contact_policy = fields.Selection(
        [
            ('warning', 'Warning Only'),
            ('block', 'Prevent Duplicates'),
        ],
        string='Duplicate Phone/Mobile Policy',
        default='warning',
        help="Warning Only: a contact can still be saved with a phone/mobile "
             "that already exists on another contact, but a warning is shown.\n"
             "Prevent Duplicates: saving a contact whose phone or mobile "
             "already exists on another contact is blocked.",
    )
