from odoo import models, fields

class AccountPaymentMethodLine(models.Model):
    _inherit = 'account.payment.method.line'

    payment_category = fields.Selection([
        ('third_party', '3rd Party'),
        ('visa', 'Visa/Card'),
        ('thiqa', 'Thiqa'),
        ('cash', 'Cash'),
    ], string="Payment Category")
