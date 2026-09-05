from odoo import fields, models

class BagWeight(models.Model):
    _name = 'bag.weight'
    _description = 'Bag Weight Configuration'

    bag_type_id = fields.Many2one('bag.type', string='Bag Type', required=True)
    weight = fields.Char(string='Bag Weight', required=True)
    note = fields.Char(string='Note')

    # Inverse relation links back to the respective slots on the Sale Order Line
    ticket_x_sale_line_id = fields.Many2one('sale.order.line', string='Ticket X Sale Line', ondelete='cascade')
    ticket_y_sale_line_id = fields.Many2one('sale.order.line', string='Ticket Y Sale Line', ondelete='cascade')