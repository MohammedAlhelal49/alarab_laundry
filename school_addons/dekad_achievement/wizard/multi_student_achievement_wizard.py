import time
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class DeMultiStudentAchievementWizard(models.TransientModel):
    """ Multi student Achievement Wizard """
    _name = "de.multi.student.achievement.wizard"
    _description = "Multi student Achievement Wizard"

    achievement_id = fields.Many2one('de.student.achievement', 'Achievement', required=True)
    achievement_image = fields.Image('image', readonly=True, store=True, related="achievement_id.image")
    achievement_type = fields.Char('Achievement Type', readonly=True, store=True,
                                   related="achievement_id.type_id.name")

    user_id = fields.Many2one('res.users', 'Given by', readonly=True, store=True, default=lambda self: self.env[
        'res.users'].browse(self.env.uid))
    reason = fields.Char('Reason', required=True)

    student_ids = fields.Many2many('de.student', string='Students', required=True)

    def do_action(self):
        students = self.student_ids
        data_list = []
        for rec in students:
            object = {}
            object['student_id'] = rec.id
            object['achievement_id'] = self.achievement_id.id
            object['user_id'] = self.user_id.id
            object['reason'] = self.reason
            data_list.append(object)
            object = {}

        achievements = self.env['de.student.achievement.assign'].create(data_list)
        action = self.env.ref('dekad_achievement.act_open_de_student_achievement_assign_view').read()[0]
        action['target'] = 'main'
        return action
