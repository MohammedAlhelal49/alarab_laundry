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

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class DeQuiz(models.Model):
    _name = "de.quiz"
    _inherit = "mail.thread"
    _description = "quiz"
    _order = "create_date DESC"

    name = fields.Char(compute='_compute_name', string='Name', store=True, readonly=True)
    grade_id = fields.Many2one('de.grade', 'Grade', readonly=True, store=True, related="classroom_id.grade_id")
    classroom_id = fields.Many2one('de.classroom', 'Classroom', required=True)

    subject_id = fields.Many2one('de.subject', string='Subject')
    type_id = fields.Many2one('de.quiz.question.group.type',
                              string='Type', required=True)
    teacher_id = fields.Many2one('de.teacher', 'Teacher', readonly=True, store=True, default=lambda self: self.env[
        'de.teacher'].search([('user_id', '=', self.env.uid)]), ondelete="cascade")
    mark = fields.Integer('Marks', store=True, readonly=True, compute="_compute_mark")
    description = fields.Text('Description', required=True)
    submission_date = fields.Datetime('Submission Date', required=True,
                                      tracking=True)

    student_ids = fields.Many2many('de.student', string='Allocated To')

    classroom_student_ids = fields.Many2many(
        'de.student', 'quiz_classroom_student_rel',
        'quiz_classroom_id', 'student_id', string="Classroom students", compute="_compute_classroom_student_ids")

    quiz_submission_ids = fields.One2many('de.quiz.submission',
                                          'quiz_id', 'Submissions')

    question_ids = fields.Many2many('de.quiz.question', string="Questions")
    attempt_ids = fields.One2many('de.quiz.submission.attempt', 'quiz_id', 'Attempts', copy=False)
    group_ids = fields.Many2many('de.quiz.question.group', string="Questions groups")

    active = fields.Boolean(default=True)

    file = fields.Binary('Attachment', copy=False)
    file_name = fields.Char(string="File Name", copy=False)  # Added by Ahmed

    correction_type = fields.Selection([
        ('manual', 'Manual'), ('automatic', 'Automatic'),

    ], 'Correction type', default='automatic', tracking=True, required=True)

    # the time configration
    hour_limit = fields.Float('Hours', required=True)
    minute_limit = fields.Float('Minutes', required=True)

    state = fields.Selection([
        ('draft', 'Draft'), ('confirm', 'Confirmed'),
        ('finish', 'Finished'),
    ], 'State', default='draft', tracking=True)

    @api.constrains('hour_limit', 'minute_limit')
    def _check_time_limit(self):
        for rec in self:
            if rec.minute_limit >= 60:
                raise exceptions.ValidationError(
                    _("Minutes cant be equal or grater than 60"))

            if (rec.hour_limit < 0 or rec.minute_limit < 0) or (rec.hour_limit == 0 and rec.minute_limit == 0):
                raise exceptions.ValidationError(
                    _("Please enter prober timing values"))

    @api.depends('subject_id', 'classroom_id')
    def _compute_name(self):
        for quiz in self:
            if quiz.subject_id \
                    and quiz.classroom_id:
                quiz.name = f"({quiz.classroom_id.display_name}) {quiz.subject_id.name}"

            else:
                quiz.name = ""

    @api.onchange('type_id')
    def onchange_type(self):
        self.group_ids = False
        self.question_ids = False

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = self.name + " (copy)"
        return super(DeQuiz, self).copy(default)

    @api.constrains('question_ids')
    def _check_questions(self):
        for rec in self:
            if not rec.question_ids:
                raise exceptions.ValidationError(
                    _("Quiz must have questions"))

    @api.depends('classroom_id')
    def _compute_classroom_student_ids(self):
        for rec in self:
            if rec.classroom_id:
                rec.classroom_student_ids = rec.classroom_id.student_ids

            else:
                rec.classroom_student_ids = False

    @api.depends('question_ids', 'question_ids.mark')
    def _compute_mark(self):
        for rec in self:
            rec.mark = sum(rec.question_ids.mapped('mark')) if rec.question_ids else 0

    @api.constrains('create_date', 'submission_date')
    def check_dates(self):
        for record in self:
            create_date = fields.Date.from_string(record.create_date)
            submission_date = fields.Date.from_string(record.submission_date)
            if create_date > submission_date:
                raise ValidationError(_(
                    "Submission Date cannot be set before Create Date."))

    # @api.onchange('grade_id')
    # def onchange_grade(self):
    #     if self.grade_id:
    #         subject_ids = self.env['de.grade'].search([
    #             ('id', '=', self.grade_id.id)]).subject_ids
    #         return {'domain': {'subject_id': [('id', 'in', subject_ids.ids)]}}

    @api.onchange('classroom_id')
    def onchange_classroom(self):
        self.student_ids = self.classroom_id.student_ids

    def set_confirm(self):
        self.state = 'confirm'

    def set_finish(self):
        self.state = 'finish'

    def set_draft(self):
        self.state = 'draft'

    def cron_close_quiz(self):
        for record in self.search([]):
            if record.submission_date <= fields.Datetime.now():
                record.set_finish()
