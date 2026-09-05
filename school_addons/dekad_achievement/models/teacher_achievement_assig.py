from odoo import models, fields


class DeTeacherAchievementAssign(models.Model):
    _name = "de.teacher.achievement.assign"
    _description = "Teacher Achievement assign"
    _rec_name = "teacher_id"
    _order = "create_date DESC , teacher_id"

    achievement_id = fields.Many2one('de.teacher.achievement', 'Achievement', required=True, ondelete="cascade")
    achievement_image = fields.Image('image', readonly=True, store=True, related="achievement_id.image")
    achievement_type = fields.Char('Achievement Type', readonly=True, store=True,
                                   related="achievement_id.type_id.name")

    teacher_id = fields.Many2one('de.teacher', 'Teacher', required=True, ondelete="cascade")

    user_id = fields.Many2one('res.users', 'Given by', readonly=True, store=True, default=lambda self: self.env[
        'res.users'].browse(self.env.uid))
    reason = fields.Char('Reason', required=True)

