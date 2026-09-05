from odoo import models, fields


class DeTeacherCreateUserWizard(models.TransientModel):
    _name = "de.teacher.create.user.wizard"
    _description = "Create user for selected Teacher(s)"

    def _get_teachers(self):
        if self.env.context and self.env.context.get('active_ids'):
            return self.env.context.get('active_ids')
        return []

    teacher_ids = fields.Many2many('de.teacher', default=_get_teachers, string='teachers')

    def create_user(self):
        active_ids = self.env.context.get('actives_ids', []) or []
        records = self.env['de.teacher'].browse(active_ids)
        records.create_user()
