from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    license_type = fields.Selection(
        selection=[
            ('trade_license', 'رخصة تجارية'),
            ('trade_name', 'الاسم التجاري'),
        ],
        string="رخصة/ الاسم التجاري"
    )
    trade_license = fields.Char(string='رخصة تجارية')
    trade_name = fields.Char(string='الاسم التجاري')