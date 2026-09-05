# -*- coding: utf-8 -*-
###############################################################################
#
#    DencCode Inc
#    Copyright (C) 2009-TODAY DencCode Inc(<http://www.dekad.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DeAssignmentSubmission(models.Model):
    _name = "de.assignment.submission"
    _inherit = "mail.thread"
    _rec_name = "assignment_id"
    _description = "Assignment Submission"
    _order = "create_date DESC"

    def _compute_is_assignment_user(self):
        for user in self:
            if self.env.user.has_group('dekad_assignment.group_de_assignment'):
                user.is_assignment_user = True
            else:
                user.is_assignment_user = False

    assignment_id = fields.Many2one(
        'de.assignment', 'Assignment', required=True, ondelete="cascade")
    student_ids = fields.Many2many(
        'de.student', store=True, readonly=True, compute="_compute_student_ids")

    student_id = fields.Many2one(
        'de.student', 'Student',
        default=lambda self: self.env['de.student'].search(
            [('user_id', '=', self.env.user.id)]), required=True, ondelete="cascade")
    description = fields.Text('Description')
    state = fields.Selection([
        ('draft', 'Draft'), ('confirm', 'Confirmed'), ('reject', 'Rejected'),
        ('accept', 'Accepted')], string='State',
        default='draft', tracking=True)
    mark = fields.Integer('Mark', tracking=True)
    notice = fields.Text('Correction Note')
    file = fields.Binary(string="solution")
    file_name = fields.Char(string="File Name") #added by Ahmed
    user_id = fields.Many2one(
        'res.users', related='student_id.user_id', string='User')
    teacher_user_id = fields.Many2one(
        'res.users', related='assignment_id.teacher_id.user_id',
        string='Teacher User')
    is_assignment_user = fields.Boolean(string='Check assignment user',
                                        compute='_compute_is_assignment_user')

    @api.depends('assignment_id')
    def _compute_student_ids(self):
        for rec in self:
            students = rec.assignment_id.student_ids
            filtered_student = students.filtered(
                lambda student: self.check_student_submission(student, rec.assignment_id))
            rec.student_ids = filtered_student

    def check_student_submission(self, student, assignment):
        if student.assignment_submission_ids.filtered(lambda submission: submission.assignment_id.id == assignment.id):
            return False
        else:
            return True

    def set_draft(self):
        self.state = 'draft'

    def set_confirm(self):
        self.state = 'confirm'

    def set_accept(self):
        self.state = 'accept'

    def set_reject(self):
        self.state = 'reject'

    def set_cancel(self):
        self.state = 'confirm'
        self.notice = ''

    @api.model_create_multi
    def create(self, vals):
        if self.env.user.child_ids:
            raise Warning(_('Invalid Action!\n Parent can not \
            create Assignment Submissions!'))
        return super(DeAssignmentSubmission, self).create(vals)

    def write(self, vals):
        if self.env.user.child_ids:
            raise Warning(_('Invalid Action!\n Parent can not edit \
            Assignment Submissions!'))
        return super(DeAssignmentSubmission, self).write(vals)

    @api.depends('assignment_id', 'student_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.assignment_id.name} - {rec.student_id.name}"



