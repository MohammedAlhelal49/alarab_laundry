from odoo import models, fields, api


class DeGrade(models.Model):
    _inherit = "de.grade"

    admission_ids = fields.One2many('de.admission', 'grade_id', string='Admissions(s)')
    admission_count = fields.Integer(compute="_compute_admission_count", string="Admission count")

    @api.depends('admission_ids')
    def _compute_admission_count(self):
        for record in self:
            record.admission_count = len(record.admission_ids)

    def action_show_admission(self):
        action = self.env.ref('dekad_admission.act_open_de_admission_view').read()[0]
        action['domain'] = [('grade_id', '=', self.id)]
        return action
