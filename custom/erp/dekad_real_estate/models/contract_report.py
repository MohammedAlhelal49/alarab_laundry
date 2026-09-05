from odoo import models, fields, api
from datetime import datetime


class ContractReport(models.TransientModel):
    _name = 'contract.report'
    _description = 'Contract Report Result'

    contract_date = fields.Date(string="Date")
    day_name = fields.Char(string="Day", compute="_compute_day_name")
    partner_id = fields.Many2one('res.partner', string="Customer")
    bank_transfer = fields.Monetary(string="Transfer")
    booking = fields.Monetary(string="Booking")
    aquda = fields.Monetary(string="Aquda")
    airbnb = fields.Monetary(string="Airbnb")
    cash = fields.Monetary(string="Cash")
    cancel_type = fields.Selection([
        ('paid_cancel', 'Cancel & Refund'),
        ('free_cancel', 'No Response'),
        ('no_show', 'Cancel without Refund'),
        ('early_checkout', 'Early Checkout'),
    ], string="Cancellation Type")

    currency_id = fields.Many2one('res.currency')
    note = fields.Text(string="Note")
    total_amount = fields.Monetary(
        string="Total",
        compute="_compute_total_amount",
        store=False,
        currency_field='currency_id'
    )

    @api.depends('bank_transfer', 'booking', 'aquda', 'airbnb', 'cash')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = (
                    (rec.bank_transfer or 0) +
                    (rec.booking or 0) +
                    (rec.aquda or 0) +
                    (rec.airbnb or 0) +
                    (rec.cash or 0)
            )

    @api.depends('contract_date')
    def _compute_day_name(self):
        days_ar = {
            'Monday': 'الإثنين',
            'Tuesday': 'الثلاثاء',
            'Wednesday': 'الأربعاء',
            'Thursday': 'الخميس',
            'Friday': 'الجمعة',
            'Saturday': 'السبت',
            'Sunday': 'الأحد',
        }

        for rec in self:
            if rec.contract_date:
                day_en = rec.contract_date.strftime('%A')
                rec.day_name = days_ar.get(day_en, day_en)
            else:
                rec.day_name = ''