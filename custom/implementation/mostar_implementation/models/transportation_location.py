from odoo import models, fields

class TransportationLocation(models.Model):
    _name = 'transportation.location'
    _description = 'Transportation Route'

    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', ondelete='cascade', required=True)
    vehicle_type_id = fields.Many2one('transportation.vehicle.type', string='Vehicle Type')
    vehicle_count = fields.Integer(string='Bag Count', default=1)
    from_location = fields.Char(string='From (Location)', required=True)
    from_datetime = fields.Datetime(string='From (Date & Time)', required=True)
    to_location = fields.Char(string='To (Location)', required=True)
    to_datetime = fields.Datetime(string='To (Date & Time)', required=True)


class TransportationVehicleType(models.Model):
    _name = 'transportation.vehicle.type'
    _description = 'Vehicle Type'

    name = fields.Char(string='Vehicle Type', required=True)