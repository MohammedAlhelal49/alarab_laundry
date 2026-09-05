from odoo import models, fields, api


class DeActivity(models.Model):
    _name = "de.activity"
    _description = "Student Activity"
    _rec_name = "type_id"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date DESC"

    type_id = fields.Many2one('de.activity.type', 'Activity Type', required=True)
    student_id = fields.Many2one('de.student', string='Student', required=True, ondelete='cascade')
    activity_time = fields.Datetime(required=True, string="Activity time")
    responsible_id = fields.Many2one('res.users', string="Responsible",
                                     domain=lambda self: self._compute_responsible_domain())
    classroom_id = fields.Many2one('de.classroom', 'Classroom', required=True)
    classroom_student_ids = fields.Many2many(
        'de.student', compute="_compute_classroom_student_ids")

    description = fields.Text('Description')
    file = fields.Binary(string="Attachment")
    file_name = fields.Char(string="File Name") #added by Ahmed
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirmed'), ('accept', 'Accepted'),
         ('reject', 'Rejected')],
        string="State", default="draft", tracking=True)

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
            if rec.classroom_id != rec.student_id.classroom_id:
                rec.student_id = False

    def set_confirm(self):
        self.state = 'confirm'

    def set_draft(self):
        self.state = 'draft'

    def set_accept(self):
        self.state = 'accept'

    def set_reject(self):
        self.state = 'reject'

    def set_cancel(self):
        self.state = 'confirm'






















