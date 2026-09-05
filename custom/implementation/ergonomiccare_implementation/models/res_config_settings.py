from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    duplicate_contact_policy = fields.Selection([
        ('warning', 'Warning Only'),
        ('block', 'Prevent Duplicates'),
    ], string="Duplicate Contacts", default='warning',
        config_parameter='ergonomiccare_implementation.duplicate_contact_policy')

    duplicate_product_policy = fields.Selection([
        ('warning', 'Warning Only'),
        ('block', 'Prevent Duplicates'),
    ], string="Duplicate Products", default='warning',
        config_parameter='ergonomiccare_implementation.duplicate_product_policy')
