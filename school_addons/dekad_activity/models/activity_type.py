from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DeActivityType(models.Model):
    _name = "de.activity.type"
    _description = "Activity Type"

    name = fields.Char('Name', required=True)

    @api.constrains('name')
    def check_name(self):
        if self.search_count([('name', '=', self.name)]) > 1:
            raise ValidationError(_(
                f"Name must be unique per activity"
            ))
