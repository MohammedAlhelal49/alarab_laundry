from odoo import models, fields, _
from odoo.exceptions import ValidationError, UserError


class DeStudentCreateWizard(models.TransientModel):
    _name = "de.student.create.user.wizard"
    _description = "Create user for selected student(s)"

    def _get_students(self):
        if self.env.context and self.env.context.get('active_ids'):
            return self.env.context.get('active_ids')
        return []

    student_ids = fields.Many2many('de.student', default=_get_students, string="Students")

    def create_user(self):
        active_ids = self.env.context.get('active_ids', []) or []
        records = self.env['de.student'].browse(active_ids)
        records.create_user()
