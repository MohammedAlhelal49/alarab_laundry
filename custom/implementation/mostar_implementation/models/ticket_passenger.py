from odoo import models, fields


class TicketPassenger(models.Model):
    _name = 'ticket.passenger'
    _description = 'Ticket Passenger'
    _rec_name = 'passenger_name'  # Ensures Odoo uses this field as the display name in dropdowns

    passenger_name = fields.Char(string="Passenger Name", required=True)
