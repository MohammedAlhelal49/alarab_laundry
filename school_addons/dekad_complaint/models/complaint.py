from odoo import models, fields, api


class DeComplaint(models.Model):
    _name = "de.complaint"
    _description = "Complaints"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "sequence"
    _order = "create_date DESC"

    sequence = fields.Char('Sequence', readonly=True, store=True, copy=False,
                           default=lambda self: self.env['ir.sequence'].sudo().next_by_code('de.complaint'))

    created_by = fields.Selection([('student', 'Student'), ('teacher', 'Teacher'), ('parent', 'Parent')], 'Created By',
                                  required=True, tracking=True)
    subject = fields.Char(string='Subject', required=True)
    student_id = fields.Many2one('de.student', 'Student', ondelete="cascade")
    teacher_id = fields.Many2one('de.teacher', 'Teacher', ondelete="cascade")
    parent_id = fields.Many2one('de.parent', 'Parent', ondelete="cascade")
    description = fields.Text(string='Description')
    file = fields.Binary('Attachment', copy=False)
    file_name = fields.Char(string="File Name",
                            copy=False)  # Added by Ahmed
    category_id = fields.Many2one('de.complaint.category', string='Category', tracking=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirmed'), ('reject', 'Reject'), ('action', 'Action taken'), ], 'state',
        required=True, default='draft', tracking=True)
    action = fields.Text(string='Action Taken')
    is_complaint_user = fields.Boolean(string='Check Complaint user')
    readonly_field = fields.Boolean(string='Readonly field')

    @api.onchange('created_by')
    def onchange_created_by(self):
        if self.created_by == 'teacher':
            self.parent_id = False
            self.student_id = False
        elif self.created_by == 'student':
            self.teacher_id = False
            self.parent_id = False
        elif self.created_by == 'parent':
            self.student_id = False
            self.teacher_id = False

    def default_get(self, fields):
        res = super(DeComplaint, self).default_get(fields)
        user = self.env.user
        if user.is_parent:
            res['created_by'] = 'parent'
            res['parent_id'] = self.env['de.parent'].search([('user_id', '=', self.env.user.id)]).id
        if user.is_student:
            res['created_by'] = 'student'
            res['student_id'] = self.env['de.student'].search([('user_id', '=', self.env.user.id)]).id

        elif user.is_teacher:
            res['created_by'] = 'teacher'
            res['teacher_id'] = self.env['de.teacher'].search([('user_id', '=', self.env.user.id)]).id
        res['is_complaint_user'] = self.env.user.has_group('dekad_complaint.group_de_complaint')
        return res

    def set_reject(self):
        self.state = 'reject'

    def set_confirm(self):
        self.state = 'confirm'

    def set_draft(self):
        self.state = 'draft'

    def set_action(self):
        self.state = 'action'

    def cancel_state(self):
        self.state = 'confirm'
        self.action = ''

    def name_get(self):
        result = []
        for record in self:
            name = record.sequence or record.subject or f'Complaint #{record.id}' or 'New Complaint'
            result.append((record.id, name))
        return result