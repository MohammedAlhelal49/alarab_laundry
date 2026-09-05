from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DeNoteGroup(models.Model):
    _name = "de.note.group"
    _description = "Note Group"

    name = fields.Char('Name', required=True)
    by_grade = fields.Boolean('Students, parents, teachers inside Grade')
    grade_ids = fields.Many2many('de.grade', string='Grades')

    all_students = fields.Boolean('All students')
    selected_students = fields.Boolean(string='Selected Students')
    student_ids = fields.Many2many('de.student', string='Students')

    all_teachers = fields.Boolean('All teachers')
    selected_teachers = fields.Boolean(string='Selected teachers')
    teacher_ids = fields.Many2many('de.teacher', string='Teachers')

    all_parents = fields.Boolean('All parents')
    selected_parents = fields.Boolean(string='Selected parents')
    parent_ids = fields.Many2many('de.parent', string='Parents')

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = self.name + " (copy)"
        return super(DeNoteGroup, self).copy(default)

    @api.constrains('name')
    def check_name(self):
        if self.search_count([('name', '=', self.name)]) > 1:
            raise ValidationError(_(
                f"Name must be unique per note group"))

    @api.onchange('by_grade', 'grade_ids')
    def onchange_grade(self):
        if self.by_grade:
            self.all_teachers = False
            self.all_students = False
            self.all_parents = False
            self.selected_students = False
            self.selected_teachers = False
            self.selected_parents = False
            self.student_ids = False
            self.parent_ids = False
            self.teacher_ids = False
            if self.grade_ids:
                teachers = self.grade_ids.mapped('teacher_ids')
                students = self.grade_ids.mapped('student_grade_ids').filtered(lambda r: r.state == 'running').mapped(
                    'student_id')
                parents = students.mapped('parent_ids')
                self.student_ids = students
                self.teacher_ids = teachers
                self.parent_ids = parents

        else:
            self.grade_ids = False
            self.student_ids = False
            self.parent_ids = False
            self.teacher_ids = False

    @api.onchange('all_students', 'selected_students')
    def onchange_student(self):
        if self.selected_students:
            self.all_students = False
        if self.all_students:
            self.selected_students = False
            self.student_ids = False

    @api.onchange('all_teachers', 'selected_teachers')
    def onchange_teacher(self):
        if self.selected_teachers:
            self.all_teachers = False
        if self.all_teachers:
            self.selected_teachers = False
            self.teacher_ids = False

    @api.onchange('all_parents', 'selected_parents')
    def onchange_parent(self):
        if self.selected_parents:
            self.all_parents = False
        if self.all_parents:
            self.selected_parents = False
            self.parent_ids = False
