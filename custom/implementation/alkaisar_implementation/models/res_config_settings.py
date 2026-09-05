from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_customer_id = fields.Many2one(
        'res.partner',
        string="Default Customer",
        domain=[('customer_rank', '>', 0)],
        default_model='res.partner',
        config_parameter='sale.sale_customer_id',
        help="This customer will be selected by default when creating new quotations."
    )
