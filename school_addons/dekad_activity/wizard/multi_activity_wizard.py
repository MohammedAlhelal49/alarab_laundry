from tokenize import group

from decorator import append

from odoo import models, fields, api


class DeMultiActivityWizard(models.TransientModel):
    _name = "de.multi.activity.wizard"
    _description = "Multi Activity Wizard"

    type_id = fields.Many2one('de.activity.type', 'Activity type', required=True)
    student_ids = fields.Many2many('de.student', string='Students', required=True)
    activity_time = fields.Datetime(string='Activity time', required=True)
    responsible_id = fields.Many2one('res.users', string="Responsible",
                                     domain=lambda self: self._compute_responsible_domain())
    classroom_id = fields.Many2one('de.classroom', 'Classroom', required=True)
    classroom_student_ids = fields.Many2many('de.student', compute="_compute_classroom_student_ids")
    file = fields.Binary(string="Attachment")
    description = fields.Text('Description')

    @api.model
    def _compute_responsible_domain(self):
        group = self.env.ref('dekad_activity.group_de_activity')
        return [('groups_id', 'in', [group.id])]

    @api.depends('classroom_id')
    def _compute_classroom_student_ids(self):
        for rec in self:
            if rec.classroom_id:
                rec.classroom_student_ids = rec.classroom_id.student_ids
            else:
                rec.classroom_student_ids = False

    @api.onchange('classroom_id')
    def _onchange_classroom(self):
        for rec in self:
            active_classroom = rec.student_ids[0].classroomm_id if rec.student_ids else False
            if rec.classroom_id != active_classroom:
                rec.student_ids = False

    def do_action(self):
        students = self.student_ids
        data_list = []
        for rec in students:
            object = {}
            object['student_id'] = rec.id
            object['file'] = self.file
            object['type_id'] = self.type_id.id
            object['activity_time'] = self.activity_time
            object['responsible_id'] = self.responsible_id.id
            object['classroom_id'] = self.classroom_id.id
            object['description'] = self.description
            data_list.append(object)
            object = {}

        activities = self.env['de.activity'].create(data_list)
        activities.set_confirm()
        action = self.env.ref('dekad_activity.act_open_de_activity_view').read()[0]
        action['target'] = 'main'
        return action
