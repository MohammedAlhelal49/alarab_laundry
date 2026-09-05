from odoo import fields, models

class BagType(models.Model):
    _name = 'bag.type'
    _description = 'Bag Type'

    name = fields.Char(string='Type Name', required=True, translate=True)