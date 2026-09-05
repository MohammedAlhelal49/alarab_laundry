from odoo import models, fields
from odoo.exceptions import UserError


class DeStudentGradeWizard(models.TransientModel):
    _name = "de.student.grade.wizard"
    _description = "Create User for selected Teacher(s)"

    student_ids = fields.Many2many('de.student', string="Student(s)")
    multi_grade = fields.Boolean(string='Multi grade(s)')
    state = fields.Selection([('running', 'Running'), ('fail', 'Failed'), ('finish', 'Finished')], string="Status",
                             default="running")

    # def default_get(self,fields):

    def default_get(self, fields):
        res = super(DeStudentGradeWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        student_grades = self.env['de.student.grade'].browse(active_ids)
        res['student_ids'] = self.env['de.student'].browse(student_grades.mapped('student_ids').ids).ids
        grades = self.env['de.grade'].browse(student_grades.mapped('grade_ids').ids)
        res['multi_grade'] = len(grades) > 1
        return res

    def wizard_save(self):
        # check if the user selected records belong to more than one grade
        active_ids = self.env.context['active_ids']
        records = self.env['de.student.grade'].browse(active_ids)
        records.write({'state': self.state})
        records.mapped('student_id').write({'classroom_id': False})
