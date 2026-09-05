from odoo import models, fields


class RealEstateBuildings(models.Model):
    _name = 'real.estate.buildings'
    _description = 'Real Estate Buildings'

    name = fields.Char(string='Name', required=True)

    city = fields.Char(string='City')
    country = fields.Many2one('res.country', string='Country')
    state = fields.Many2one('res.country.state', string='State')
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    zip = fields.Char(string='ZIP')

    location = fields.Char(string='Location')
    number_of_floors = fields.Integer(string='No. of Floors')
    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        domain=[('res_model', '=', 'real.estate.buildings')],
        string='Attachments'
    )