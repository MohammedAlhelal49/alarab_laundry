import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResUser(models.Model):
    _inherit = 'res.users'

    # Basic status fields
    is_blocked = fields.Boolean(string="Is Blocked", default=False)
    is_suspended = fields.Boolean(string="Is Suspended", default=False)

    # Student relationships
    student_line = fields.Many2one('de.student', string='Student Record')
    user_line = fields.One2many('de.student', 'user_id', string='Student Records')

    # Other relationships
    child_ids = fields.Many2many('res.users', relation='res_user_first_rel1',
                                 column1='user_id', column2='res_user_second_rel1',
                                 string="Children Users")

    student_ids = fields.Many2many('de.student', string='Associated Students')

    # Computed field
    role = fields.Char(string='User Role', compute="_compute_role", store=False)

    @api.depends('is_student', 'is_teacher')
    def _compute_role(self):
        for rec in self:
            if rec.is_student:
                rec.role = "Student User"
            elif rec.is_teacher:
                rec.role = "Teacher User"
            else:
                rec.role = "Employee User"

    def check_role_email_duplication(self, data_object={}):
        teachers = self.env['de.teacher'].search([])
        roles = ([('teacher', teacher.id, teacher.email, teacher.name) for teacher in teachers])
        for role in roles:
            # in case of the update
            same_record = data_object['role'] == role[0] and data_object['id'] == role[1]
            if data_object['id']:
                if role[2] == data_object['email'] and not same_record:
                    raise ValidationError(
                        _(f'The email ({role[2]}) is already associated with {role[0]} user ({role[3]}).'))
            else:
                if role[2] == data_object['email']:
                    raise ValidationError(_(
                        f'The email ({role[2]}) is already associated with {role[0]} user ({role[3]}).'
                    ))

    def check_role_name_duplication(self, data_object={}):
        students = self.env['de.student'].search([])
        teachers = self.env['de.teacher'].search([])
        roles = ([('teacher', teacher.id, teacher.name) for teacher in teachers] + [
            ('student', student.id, student.name) for student in students
        ])
        for role in roles:
            # in case of update
            same_record = data_object['role'] == role[0] and data_object['id'] == role[1]
            if data_object['id']:
                if role[2] == data_object['name'] and not same_record:
                    raise ValidationError(_(
                        f'The name ({role[2]}) is already used in {role[0]} user'))
            else:
                if role[2] == data_object['name']:
                    raise ValidationError(_(
                        f'The name ({role[2]}) is already used in {role[0]} user'
                    ))

class ResPartner(models.Model):
    _inherit = 'res.partner'
    religion_id = fields.Many2one('de.religion', string='Religion')
    country_group_id = fields.Many2one('res.country.group', string="Nationality Group")
    nationality_id = fields.Many2one('res.country', string="Nationality")

    is_student = fields.Boolean(string="Is Student")
    is_teacher = fields.Boolean(string="Is Teacher")


class ResGroups(models.Model):
    _inherit = 'res.groups'
    sequence = fields.Integer(string="Sequence")
    hidden = fields.Boolean(string="hidden", default=False)
