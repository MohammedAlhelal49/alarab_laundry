from odoo import fields, models


class PDCWizard(models.Model):
    _inherit = 'pdc.wizard'

    payment_order = fields.Integer(
        string='Payment Order'
    )