from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DeParentRelation(models.Model):
    _name = "de.parent.relationship"
    _description = "Relationships"

    name = fields.Char('Name', required=True)

    @api.constrains('name')
    def check_name(self):
        if self.search_count([('name', '=', self.name)]) > 1:
            raise ValidationError(_(
                'Relation must be unique'
            ))
