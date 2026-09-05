from odoo import models, fields


class DeStudentAchievementAssign(models.Model):
    _name = "de.student.achievement.assign"
    _description = "Student Achievement assign"
    _rec_name = "student_id"
    _order = "create_date DESC , student_id"

    achievement_id = fields.Many2one('de.student.achievement', 'Achievement', required=True, ondelete="cascade")
    achievement_image = fields.Image('image', readonly=True, store=True, related="achievement_id.image")
    achievement_type = fields.Char('Achievement Type', readonly=True, store=True,
                                   related="achievement_id.type_id.name")

    student_id = fields.Many2one('de.student', 'Student', required=True, ondelete="cascade")

    user_id = fields.Many2one('res.users', 'Given by', readonly=True, store=True, default=lambda self: self.env[
        'res.users'].browse(self.env.uid))
    reason = fields.Char('Reason', required=True)

