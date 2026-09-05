from odoo import fields, models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    related_invoice_number = fields.Char(compute="_compute_related_invoice_number")
    service_type = fields.Selection([
        ('ticket', 'Ticket'),
        ('hotel', 'Hotel'),
        ('transportation', 'Transportation'),
        ('tours_packages', 'Tours & Packages')
    ], string='Service Type')

    ticket_type = fields.Selection([
        ('departure', 'Departure'),
        ('return', 'Return'),
        ('round_trip', 'Round-trip')
    ], string='Ticket Type', default='round_trip', required=True)

    # Departure Ticket Parameters
    ticket_x_leave_date = fields.Datetime(string='Departure Ticket Leave Date')
    ticket_x_arrive_date = fields.Datetime(string='Departure Ticket Arrive Date')
    ticket_x_leave_notes = fields.Text(string='Description')
    ticket_x_arrive_notes = fields.Text(string='Description')
    ticket_x_from = fields.Char(string='Departure From')
    ticket_x_to = fields.Char(string='Departure To')
    ticket_x_number = fields.Char(string='Departure Ticket Number')
    ticket_x_plane_number = fields.Char(string='Departure Flight Number')
    ticket_x_bnr = fields.Char(string='Departure PNR')
    ticket_x_seat_number = fields.Char(string='Departure Seat Number')
    ticket_x_passenger_ids = fields.Many2many(
        comodel_name='ticket.passenger',
        relation='sale_order_line_ticket_x_passenger_rel',  # <--- Explicit relation table
        column1='sale_line_id',
        column2='passenger_id',
        string="Departure Passengers"
    )
    ticket_x_bag_weight_ids = fields.One2many(
        'bag.weight', 'ticket_x_sale_line_id', string='Departure Ticket Bag Weights'
    )

    # Return Ticket Parameters
    ticket_y_leave_date = fields.Datetime(string='Return Ticket Leave Date')
    ticket_y_arrive_date = fields.Datetime(string='Return Ticket Arrive Date')
    ticket_y_leave_notes = fields.Text(string='Description')
    ticket_y_arrive_notes = fields.Text(string='Description')
    ticket_y_from = fields.Char(string='Return From')
    ticket_y_to = fields.Char(string='Return To')
    ticket_y_number = fields.Char(string='Return Ticket Number')
    ticket_y_plane_number = fields.Char(string=' Return Flight Number')
    ticket_y_bnr = fields.Char(string='Return PNR')
    ticket_y_seat_number = fields.Char(string='Return Seat Number')
    ticket_y_passenger_ids = fields.Many2many(
        comodel_name='ticket.passenger',
        relation='sale_order_line_ticket_y_passenger_rel',  # <--- Explicit distinct relation table
        column1='sale_line_id',
        column2='passenger_id',
        string="Return Passengers"
    )
    ticket_y_bag_weight_ids = fields.One2many(
        'bag.weight', 'ticket_y_sale_line_id', string='Return Ticket Bag Weights'
    )

    # Hotel Parameters
    hotel_name = fields.Char(string='Hotel Name')
    hotel_number = fields.Char(string='Hotel Number (HCN)')
    hotel_country_id = fields.Many2one('res.country', string='Country')
    hotel_street = fields.Char(string='Street Address')
    hotel_check_in_date = fields.Datetime(string='Check-in Date')
    hotel_check_out_date = fields.Datetime(string='Check-out Date')
    booking_id = fields.Char(
        string='Booking ID',
    )
    hotel_room_ids = fields.One2many(
        'hotel.room.detail', 'sale_line_id', string='Rooms Details'
    )

    @api.depends('invoice_lines')
    def _compute_related_invoice_number(self):
        for line in self:
            line.related_invoice_number = line.invoice_lines[0].move_id.name[-5:] if line.invoice_lines else ""

    # Transportation Parameters
    transportation_type = fields.Selection([
        ('with_driver', 'With Driver'),
        ('without_driver', 'Without Driver')
    ], string='Transportation Type')

    transportation_location_ids = fields.One2many(
        'transportation.location', 'sale_line_id', string='Locations Table'
    )

    tours_ids = fields.One2many(
        'tour.tour', 'sale_line_id', string='Tours Details'
    )

    tour_hotel_ids = fields.One2many(
        'tour.hotel', 'sale_line_id', string='Tour Hotel Details'
    )

    def action_open_line_form_view(self):
        """Action button to trigger a clean modal focus view utilizing our dedicated form view."""
        self.ensure_one()

        # Fetch the XML ID of our new form view
        view_id = self.env.ref('mostar_implementation.view_sale_order_line_form_modal').id

        return {
            'name': 'Detailed Order Line Configurations',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'view_mode': 'form',
            'res_id': self.id,
            'view_id': view_id,
            'target': 'new',
        }
