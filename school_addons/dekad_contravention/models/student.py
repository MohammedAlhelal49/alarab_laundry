from odoo import models, fields, api


class DeStudent(models.Model):
    _inherit = 'de.student'

    contravention_ids = fields.One2many(
        'de.contravention', 'student_id', 'Contraventions')
    suspend_ids = fields.One2many(
        'de.student.suspend', 'student_id', 'Suspends')
    contravention_count = fields.Integer('Contravention count', compute='compute_contravention_count', readonly=True,
                                         store=True)

    @api.depends("contravention_ids")
    def compute_contravention_count(self):
        for record in self:
            record.contravention_count = len(record.contravention_ids)

    def action_show_contravention(self):
        action = self.env.ref('dekad_contravention.act_open_de_contravention_view').read()[0]
        action['domain'] = [('student_id', '=', self.id)]
        return action





