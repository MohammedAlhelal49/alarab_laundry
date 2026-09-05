from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DeComplaintCategory(models.Model):
    _name = "de.complaint.category"
    _description = "Complaint category"

    name = fields.Char(string='Name', required=True)
    type = fields.Selection([('academic', 'Academic'), ('non-academic', 'Non Academic')], string='Type', required=True)

    @api.constrains('name')
    def check_name(self):
        if self.search_count([('name', '=', self.name)]) > 1:
            raise ValidationError(_(
                f"Name must be unique per category"
            ))
