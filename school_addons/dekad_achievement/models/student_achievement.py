from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DeStudentAchievement(models.Model):
    _name = "de.student.achievement"
    _description = "Students Achievements"
    image = fields.Image('Image', copy=False)
    type_id = fields.Many2one('de.achievement.type', 'Type', required=True)
    name = fields.Char('Name', required=True)
    description = fields.Text('Description')

    @api.constrains('name')
    def check_name(self):
        if self.search_count([('name', '=', self.name)]) > 1:
            raise ValidationError(_(
                f"Name must be unique per achievement"))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = self.name + " (copy)"
        return super(DeStudentAchievement, self).copy(default)
