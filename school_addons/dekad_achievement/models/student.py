from odoo import models,fields,api
from odoo.api import readonly


class DeStudent(models.Model):
    _inherit = 'de.student'
    achievement_ids =fields.One2many('de.student.achievement.assign','student_id',string='Achievements')
    achievement_count =fields.Integer('Achievement.count',compute='compute_achievement_count',readonly=True,store=True)

    @api.depends("achievement_ids")
    def compute_achievement_count(self):
        for record in self:
            record.achievement_count = len(record.achievement_ids)