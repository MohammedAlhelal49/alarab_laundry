from odoo import models, fields, api


class DeGrade(models.Model):
    _name = 'de.grade'
    _inherit = 'mail.thread'
    _description = 'Grade'

    name = fields.Char(string='Grade', required=True, translate=True)
    section = fields.Selection([
        ('kindergarten', 'Kindergarten'),
        ('primary', 'Primary'),
        ('intermediate', 'Intermediate'),
        ('secondary', 'Secondary'),
    ], 'Section', required=True)

    color = fields.Integer(default=0, string='Color', copy=False)
    active = fields.Boolean(default=True, copy=False)
    # subjects
    subject_ids = fields.One2many('de.subject', 'grade_id', 'Subjects')
    subject_count = fields.Integer(compute='_compute_subject_count', readonly=True, store=True)

    # teachers
    teacher_ids = fields.Many2many('de.teacher', string='Teachers', store=True, readonly=True,
                                   compute='_compute_teacher_ids')
    teacher_count = fields.Integer(store=False, readonly=True, compute='_compute_teacher_count')

    # student
    student_grade_ids = fields.One2many('de.student.grade', 'grade_id', 'student grades')
    student_count = fields.Integer(compute='compute_student_count', readonly=True, store=True, string="Student")

    _sql_constraints = [
        ('name_unique', 'Unique (name)', 'Grade must be unique'),
    ]

    @api.depends('subject_ids')
    def _compute_subject_count(self):
        for record in self:
            record.subject_count = len(record.subject_ids)

    @api.depends('student_grade_ids')
    def compute_student_count(self):
        for record in self:
            record.student_count = len(
                record.student_grade_ids.filtered(lambda item: item.state == 'running').mapped('student_id'))

    @api.depends('subject_ids', 'teacher_ids.subject_ids')
    def _compute_teacher_ids(self):
        for record in self:
            record.teacher_ids = self.env['de.teacher'].search([('subject_ids', 'in', record.subject_ids.ids)])

    @api.depends('teacher_ids')
    def _compute_teacher_count(self):
        for record in self:
            record.teacher_count = len(record.teacher_ids)

    def action_show_subject(self):
        self.ensure_one()
        action = self.env.ref('dekad_core.act_open_de_subject_view').read()[0]
        action['domain'] = [('id', 'in', self.subject_ids.ids)]
        action['context'] = {'default_grade_id': self.id}
        return action

    def action_show_teacher(self):
        action = self.env.ref('dekad_core.act_open_de_teacher_view').read()[0]
        action['domain'] = [('subject_ids', 'in', self.subject_ids.ids)]
        action['context'] = {'create': False, 'edit': False}
        return action

    def action_show_student(self):
        action = self.env.ref('dekad_core.act_open_de_student_view').read()[0]
        action['domain'] = [(
            'student_grade_ids.grade_id', '=', self.id
        ), ('student_grade_ids.state', '=', 'running')]
        action['context'] = {'create': False, 'edit': False}
        return action
