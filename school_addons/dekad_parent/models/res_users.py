import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _compute_role(self):
        for rec in self:
            if rec.is_student:
                rec.role = "Student user"
            elif rec.is_parent:
                rec.role = "Parent user"
            elif rec.is_teacher:
                rec.role = "Teacher user"
            else:
                rec.role = "Employee user"

    def check_role_email_duplication(self, data_object={}):
        teachers = self.env['de.teacher'].search([])
        parents = self.env['de.parent'].search([]) if self.env['ir.model'].search([('model', '=', 'de.parent')]) else []
        roles = ([('teacher', teacher.id, teacher.email, teacher.name) for teacher in teachers] + [
            ('parent', parent.id, parent.email, parent.name) for parent in parents])
        for role in roles:
            # in the case of update
            same_record = data_object['role'] == role[0] and data_object['id'] == role[1]
            if data_object['id']:
                if role[2] == data_object['email'] and not same_record:
                    raise ValidationError(_(
                        f'The email ({role[2]}) is already associated with {role[0]} user ({role[3]}).'))
            else:
                if role[2] == data_object['email']:
                    raise ValidationError(_(
                        f'The email ({role[2]}) is already associated with {role[0]} user ({role[3]})/'
                    ))

    def check_role_name_duplication(self, data_object={}):
        students = self.env['de.student'].search([])
        teachers = self.env['de.teacher'].search([])
        parents = self.env['de.parent'].search([])
        roles = ([('teacher', teacher.id, teacher.name) for teacher in teachers] + [
            ('parent', parent.id, parent.name) for parent in parents
        ] + [('student', student.id, student.name) for student in students])

        for role in roles:
            # in the case of update
            same_record = data_object['role'] == role[0] and data_object['id'] == role[1]
            if data_object['id']:
                if role[2] == data_object['name'] and not same_record:
                    raise ValidationError(_(f'The name ({role[2]}) is already used in {role[0]} user'))
            else:
                if role[2] == data_object['name']:
                    raise ValidationError(_(
                        f'The name({role[2]}) is already used in {role[0]} user'
                    ))


class ResPartner(models.Model):
    _inherit = 'res.partner'
    is_parent = fields.Boolean(string="Is a parent")
