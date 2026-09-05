from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vendor_id = fields.Many2one(
        'res.partner',
        string="Default Vendor",
        default_model='res.partner',
        config_parameter='purchase.vendor_id',
        help="The temporary vendor assigned to new RFQs."
    )