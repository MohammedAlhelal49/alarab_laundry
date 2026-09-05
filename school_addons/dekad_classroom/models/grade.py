from odoo import models, fields, api


class DeGrade(models.Model):
    _inherit = "de.grade"

    classroom_ids = fields.One2many('de.classroom', 'grade_id', string='Classroom(s)')
    classroom_count = fields.Integer(compute='_compute_classroom_count', store=True, readonly=True)
    max_student_count = fields.Integer(compute='_compute_max_student_count', store=True, readonly=True,
                                       string="Student capacity")

    @api.depends('classroom_ids')
    def _compute_classroom_count(self):
        for record in self:
            record.classroom_count = len(record.classroom_ids)

    @api.depends('classroom_ids', 'classroom_ids.capacity')
    def _compute_max_student_count(self):
        for record in self:
            max_student_count = 0
            for rec in record.classroom_ids:
                max_student_count += rec.capacity
            record.max_student_count = max_student_count

    # redefine action_show_ to modify action's bottoms in grade view
    def action_show_classroom(self):
        action = self.env.ref('dekad_classroom.act_open_de_classroom_view').read()[0]
        action['domain'] = [('grade_id', '=', self.id)]
        action['context'] = {'default_grade_id': self.id}
        return action
