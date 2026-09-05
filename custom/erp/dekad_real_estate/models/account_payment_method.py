from odoo import models, fields

class AccountPaymentMethodLine(models.Model):
    _inherit = 'account.payment.method.line'

    real_estate_payment_category = fields.Selection([
        ('bank_transfer', 'Transfer'),
        ('booking', 'Booking.com'),
        ('aquda', 'Aquda'),
        ('airbnb', 'Airbnb'),
        ('cash', 'Cash'),
    ], string="Payment Category")
