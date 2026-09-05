from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DeContraventionCategory(models.Model):
    _name = "de.contravention.category"
    _description = "Contravention category"

    name = fields.Char('Name', required=True)
    type = fields.Selection([('major', 'Major'), ('minor', 'Minor')], string="Type", required=True)

    @api.constrains('name')
    def check_name(self):
        if self.search_count([('name', '=', self.name)]) > 1:
            raise ValidationError(_(
                f"Name must be unique per category"))
