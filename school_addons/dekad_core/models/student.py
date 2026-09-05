from odoo import models, fields, api
import http.client
import json


class DeStudentGrade(models.Model):
    _name = "de.student.grade"
    _description = "Student grade Details"
    _inherit = "mail.thread"
    _order = "grade_id,student_id"

    student_id = fields.Many2one('de.student', 'Student',
                                 ondelete="cascade", tracking=True)
    grade_id = fields.Many2one('de.grade', 'Grade', tracking=True, ondelete="cascade")
    finish_grade_date = fields.Date()
    sequence = fields.Char('Sequence', readonly=True, store=True,
                           default=lambda self: self.env['ir.sequence'].next_by_code('de.student.grade'))

    subject_ids = fields.Many2many('de.subject', string="Subjects", readonly=True, store=True)

    academic_year_id = fields.Many2one('de.academic.year', 'Academic Year')
    state = fields.Selection([('running', 'Running'), ('fail', 'failed'),
                              ('finish', 'Finished')],
                             string="Status", default="running")

    @api.model
    def action_do(self):
        print('data here')

    def set_running(self):
        self.state = 'running'

    def set_fail(self):
        self.state = 'fail'
        self.student_id.classroom_id = False

    def set_finish(self):
        self.state = 'finish'
        self.student_id.classroom_id = False

    @api.depends('grade_id', 'student_id', 'state')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.grade_id.name} - {rec.student_id.name} - {rec.state}"


class DeStudent(models.Model):
    _name = "de.student"
    _description = "Student"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {"res.partner": "partner_id"}
    partner_id = fields.Many2one('res.partner', 'Contact',
                                 required=True, ondelete="cascade")
    # name fields +++++++++++++++++++++
    first_name = fields.Char('First Name')
    middle_name = fields.Char('Middle Name')
    last_name = fields.Char('Last Name')
    detailed_name = fields.Boolean('Detailed name')

    # emirate id fields +++++++++++++++++++++
    emirate_id = fields.Char('Emirate Id')
    emirate_id_expiry_date = fields.Date('Emirate Id Expiry Date')

    # personal fields and sequence
    birth_date = fields.Date('Birth Date')
    address = fields.Text("Full address")
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female')
    ], 'Gender', required=True)
    visa_info = fields.Char('Visa Info', size=64)
    sequence = fields.Char('Sequence', readonly=True, store=True, copy=False,
                           default=lambda self: self.env['ir.sequence'].next_by_code('de.student'))

    # student special fields

    student_no = fields.Char('Student No')
    family_book_no = fields.Char('Family Book No')
    esis_no = fields.Char('ESIS No')

    # user access fields +++++++++++++++++++++

    user_id = fields.Many2one('res.users', 'User', copy=False)
    is_blocked = fields.Boolean('Is blocked', copy=False, related="user_id.is_blocked")
    is_suspended = fields.Boolean('Is Suspended', copy=False, related="user_id.is_suspended")

    # grade fields +++++++++++++++++++++
    student_grade_ids = fields.One2many('de.student.grade', 'student_id', 'Grade Details')
    grade = fields.Many2one('de.grade',
                            'Grade', compute="compute_grade", store=True, readonly=True,
                            )
    active = fields.Boolean(default=True)

    @api.onchange('first_name', 'middle_name', 'last_name')
    def _onchange_name(self):
        if self.first_name and self.middle_name and self.last_name:
            self.name = str(self.first_name) + " " + str(
                self.middle_name) + " " + str(self.last_name)

    @api.depends('student_grade_ids')
    def compute_grade(self):
        for record in self:
            if record.student_grade_ids:
                record.grade = record.student_grade_ids.filtered(lambda r: r.state == 'running').mapped('grade_id')
            else:
                record.grade = False
        return False

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = self.name + " (copy)"

        return super(DeStudent, self).copy(default)

    def create_user(self):
        user_group = self.env.ref("base.group_portal") or False
        users_res = self.env['res.users']
        for record in self:
            if not record.user_id:
                user_id = users_res.create({
                    'name': record.name,
                    'partner_id': record.partner_id.id,
                    'login': record.name.replace(' ', '').lower(),
                    'groups_id': user_group,
                    'is_student': True,
                    'tz': self._context.get('tz'),

                })
                record.user_id = user_id

    def unlink(self):
        for rec in self:
            rec.user_id.unlink() if rec.user_id else 1 == 1
        return super(DeStudent, self).unlink()

    @api.model_create_multi
    def create(self, vals):
        self.env['res.users'].check_role_name_duplication({'id': 0, 'role': 'student', 'name': vals[0]['name']})
        res = super(DeStudent, self).create(vals)
        res.is_student = True
        return res

    def cron_clear_unused_contact(self):
        student_env = self.env['de.student']
        student_contacts = student_env.search([]).mapped('partner_id')
        contacts = self.env['res.partner'].search(
            [('is_student', '=', True)])
        for item in contacts:
            if item not in student_contacts:
                item.unlink()

    def block_user(self):
        for rec in self:
            rec.user_id.is_blocked = True

    def unblock_user(self):
        for rec in self:
            rec.user_id.is_blocked = False

    @api.constrains('name')
    def check_role_name(self):
        self.env['res.users'].check_role_name_duplication({'id': self.id, 'role': 'student', 'name': self.name})
