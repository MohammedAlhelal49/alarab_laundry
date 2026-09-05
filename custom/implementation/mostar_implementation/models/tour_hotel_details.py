from odoo import models, fields, api


class TourHotelDetails(models.Model):
    _name = 'tour.hotel'
    _description = 'Tour Hotel Details'

    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', ondelete='cascade', required=True)
    booking_id = fields.Char(string='Booking ID')
    hotel_name = fields.Char(string='Hotel Name')
    hotel_number = fields.Char(string='Hotel Number (HCN)')
    hotel_check_in_date = fields.Datetime(string='Check-in Date')
    hotel_check_out_date = fields.Datetime(string='Check-out Date')

    hotel_type_id = fields.Many2one(
        'product.attribute.value',
        string='Room Category',
        domain="[('attribute_id.name', '=', 'Room Category')]",
        help="Select room category dynamically from product attributes."
    )

    meal_id = fields.Many2one(
        'product.attribute.value',
        string='Meal',
        domain="[('attribute_id.name', '=', 'Meals Hotels')]",
        help="Select meal dynamically from product attributes."
    )

    guest_number = fields.Char(string='Guest Number')
    night_number = fields.Char(string='Night Number')
