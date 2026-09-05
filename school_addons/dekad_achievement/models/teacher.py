from odoo import models, fields, api


class DeTeacher(models.Model):
    _inherit = 'de.teacher'
    achievement_ids = fields.One2many('de.teacher.achievement.assign', 'teacher_id', string='Achievements')
    achievement_count = fields.Integer('Achievement count', compute='compute_achievement_count', readonly=True,
                                       store=True)

    @api.depends("achievement_ids")
    def compute_achievement_count(self):
        for record in self:
            record.achievement_count = len(record.achievement_ids)

