from odoo import models, fields, api
from datetime import datetime, timedelta


class DeStudentSuspend(models.Model):
    _name = "de.student.suspend"
    _description = "Student Suspends"
    _rec_name = "student_id"
    _order = "create_date DESC , student_id"
    student_id = fields.Many2one('de.student', 'Student', ondelete='cascade')
    contravention_id = fields.Many2one('de.contravention', 'Contravention', ondelete='cascade')
    start_date = fields.Date('Suspend From')
    end_date = fields.Date('Suspend To')

    @api.depends('start_date', 'end_date')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.start_date} : {rec.end_date}"
