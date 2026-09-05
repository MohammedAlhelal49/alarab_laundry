from odoo import fields, models

class HotelRoomDetail(models.Model):
    _name = 'hotel.room.detail'
    _description = 'Hotel Room Detail'

    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', ondelete='cascade')
    room_number = fields.Char(string='Room Number')
    persons_number = fields.Char(string='Guest Number')
    gender = fields.Char(string='Number of Nights')
    note = fields.Char(string='Details or Notes')