from odoo import models, fields, api


class DeStudentPenalty(models.Model):
    _name = "de.student.penalty"
    _description = "Student penalties"
    _rec_name = "student_id"
    _order = "create_date DESC , student_id"
    penalty = fields.Integer('Penalty Amount')
    student_id = fields.Many2one('de.student', 'Student', ondelete='cascade')
    contravention_id = fields.Many2one('de.contravention', 'Contravention', ondelete='cascade')

    @api.depends('penalty')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.penalty
