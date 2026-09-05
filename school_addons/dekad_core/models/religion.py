from odoo import models, fields, api


class DeReligion(models.Model):
    _name = "de.religion"
    _description = "School religions"
    name = fields.Char(string="Name", required=True)
    _sql_constraints = [(
        'unique_name', 'unique(name)', 'Name should be unique per religion!'
    )]
