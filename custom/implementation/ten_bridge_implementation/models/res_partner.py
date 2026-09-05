from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'


    trade_license = fields.Char(string='رخصة تجارية')
    trade_name = fields.Char(string='الاسم التجاري')
    fax = fields.Char(
        string='رقم الفاكس'
    )

    po_box = fields.Char(
        string='صندوق البريد'
    )

    name_ar = fields.Char(
        string='Name (Arabic)'
    )