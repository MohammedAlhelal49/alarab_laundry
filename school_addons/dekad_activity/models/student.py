from odoo import models, fields, api


class DeStudent(models.Model):
    _inherit = "de.student"

    activity_log_ids = fields.One2many('de.activity', 'student_id', string='Activity Lof')
    activity_count = fields.Integer(compute='compute_activity_count', readonly=True, store=True)

    def action_show_activity(self):
        action = self.env.ref('dekad_activity.'
                              'act_open_de_activity_view').read()[0]
        action['domain'] = [('student_id', 'in', self.ids)]
        return action

    @api.depends('activity_log_ids')
    def compute_activity_count(self):
        for record in self:
            record.activity_count = len(record.activity_log_ids)
