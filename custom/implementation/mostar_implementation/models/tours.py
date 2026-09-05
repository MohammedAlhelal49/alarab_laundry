from odoo import models, fields

class Tour(models.Model):
    _name = 'tour.tour'
    _description = 'Tour Details'
    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', ondelete='cascade', required=True)
    details = fields.Char(string='Details', required=True)
    details_date = fields.Datetime(string='Datetime', required=True)