from odoo import models, fields, api

class MeterReading(models.Model):
    _name = 'meter.reading'
    _description = 'Meter Reading'
    _order = 'meter_id, date'

    invoice_id = fields.Many2one('account.move', string='Invoice',store=True)
    usage = fields.Float(string='Usage',compute='_compute_usage',store=True, readonly=True)
    date = fields.Date(string='Date', required=True,store=True)
    quantity = fields.Float(string='Quantity',store=True)
    description = fields.Char(string='Description',store=True)
    account_analytic_account_id = fields.Many2one('account.analytic.account', string='Property',store=True)
    meter_id = fields.Many2one('real.estate.meters', string='Meter',store=True)
    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sale Order',
        domain="[('account_analytic_account_id', '!=', False)]",
        ondelete='set null',
        copy=True,
        store=True,
    )

    @api.depends('quantity', 'date', 'meter_id')
    def _compute_usage(self):
        for record in self:
            # Search all meter readings for the same meter, up to and including this record
            domain = [
                ('meter_id', '=', record.meter_id.id),
                ('date', '<=', record.date),
                ('id', '!=', record.id),  # Exclude self to avoid zero result
            ]
            previous_readings = self.search(domain, order='date desc, id desc', limit=1)
            if previous_readings:
                record.usage = record.quantity - previous_readings.quantity
            else:
                record.usage = 0.0