# -*- coding: utf-8 -*-
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    custom_salutation = fields.Selection([
        ('Mr.', 'Mr.'),
        ('Mrs.', 'Mrs.'),
    ], string='Salutation')

    x_passport_number = fields.Char(string='Passport Number')
    x_nationality_id = fields.Many2one('res.country', string='Nationality')