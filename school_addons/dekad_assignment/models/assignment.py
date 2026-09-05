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


class DeAssignment(models.Model):
    _name = "de.assignment"
    _inherit = "mail.thread"
    _description = "Assignment"
    _order = "create_date DESC"

    name = fields.Char(compute='_compute_name', string='Name', store=True, readonly=True)
    grade_id = fields.Many2one('de.grade', 'Grade', readonly=True, store=True, related="classroom_id.grade_id")
    classroom_id = fields.Many2one('de.classroom', 'Classroom', required=True)

    subject_id = fields.Many2one('de.subject', string='Subject', required=True)
    assignment_type = fields.Many2one('de.assignment.type',
                                      string='Assignment Type', required=True)
    teacher_id = fields.Many2one('de.teacher', 'Teacher', readonly=True, store=True, default=lambda self: self.env[
        'de.teacher'].search([('user_id', '=', self.env.uid)]), ondelete="cascade")

    mark = fields.Integer('Mark', required=True)
    description = fields.Text('Description', required=True)
    submission_date = fields.Datetime('Submission Date', required=True,
                                      tracking=True)

    student_ids = fields.Many2many('de.student', string='Allocated To', required=True)

    classroom_student_ids = fields.Many2many(
        'de.student', 'assignment_classroom_student_rel',
        'assignment_classroom_id', 'student_id', string="Classroom students", compute="_compute_classroom_student_ids")

    assignment_submission_ids = fields.One2many('de.assignment.submission',
                                                'assignment_id', 'Submissions')

    active = fields.Boolean(default=True)

    file = fields.Binary(string="Attachment", copy=False)
    file_name = fields.Char(string="File Name") #added by Ahmed

    state = fields.Selection([
        ('draft', 'Draft'), ('confirm', 'Confirmed'),
        ('finish', 'Finished'),
    ], 'State', default='draft', tracking=True)

    @api.depends('classroom_id')
    def _compute_classroom_student_ids(self):
        for rec in self:
            if rec.classroom_id:
                rec.classroom_student_ids = rec.classroom_id.student_ids
            else:
                rec.classroom_student_ids = False

    @api.constrains('create_date', 'submission_date')
    def check_dates(self):
        for record in self:
            create_date = fields.Date.from_string(record.create_date)
            submission_date = fields.Date.from_string(record.submission_date)
            if create_date > submission_date:
                raise ValidationError(_(
                    "Submission Date cannot be set before Create Date."))

    @api.onchange('grade_id')
    def onchange_grade(self):
        for record in self:
            record.subject_id = False


    @api.onchange('classroom_id')
    def onchange_classroom(self):
        self.student_ids = self.classroom_id.student_ids

    def set_confirm(self):
        self.state = 'confirm'

    def set_finish(self):
        self.state = 'finish'

    def set_draft(self):
        self.state = 'draft'

    def cron_close_assignment(self):
        for record in self.env['de.assignment'].search([]):
            if record.submission_date <= fields.Datetime.now():
                record.set_finish()

    @api.depends('subject_id', 'classroom_id')
    def _compute_name(self):
        for assignment in self:
            if assignment.subject_id \
                    and assignment.classroom_id:
                assignment.name = f"({assignment.classroom_id.display_name}) {assignment.subject_id.name}"
            else:
                assignment.name = ""

            # For record rule on student and teacher dashboard

    ## function for the demo
    def correct_submission(self):
        for assignment in self:
            for submission in assignment.assignment_submission_ids:
                submission.set_accept()
                submission.mark = 70
                submission.notice = "Correction notes"
