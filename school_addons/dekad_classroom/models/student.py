from odoo import models, fields, api


class DeStudent(models.Model):
    _inherit = "de.student"

    classroom_id = fields.Many2one('de.classroom', string='Classroom')


class DeStudentGrade(models.Model):
    _inherit = "de.student.grade"
    classroom_id = fields.Many2one('de.classroom', string="Classroom", compute="_compute_classroom_id")

    @api.depends('student_id')
    def _compute_classroom_id(self):
        for rec in self:
            rec.classroom_id = rec.student_id.classroom_id
