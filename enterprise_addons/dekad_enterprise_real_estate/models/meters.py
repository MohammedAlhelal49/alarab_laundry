from odoo import models, fields


class RealEstateMeters(models.Model):
    _name = 'real.estate.meters'
    _description = 'Real Estate Meters'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Description')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id)
    price = fields.Monetary(string='Price', currency_field='currency_id')
