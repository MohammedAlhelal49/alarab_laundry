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


class DeQuizSubmission(models.Model):
    _name = "de.quiz.submission"
    _inherit = "mail.thread"
    _rec_name = "quiz_id"
    _description = "quiz Submission"
    _order = "create_date DESC"

    def _compute_is_quiz_user(self):
        for user in self:
            if self.env.user.has_group('dekad_quiz.group_de_quiz'):
                user.is_quiz_user = True
            else:
                user.is_quiz_user = False

    def _compute_user_boolean(self):
        for user in self:
            if self.env.user.has_group('dekad_quiz.group_de_quiz'):
                user.user_boolean = True
            else:
                user.user_boolean = False

    quiz_id = fields.Many2one(
        'de.quiz', 'quiz', required=True, ondelete="cascade")
    student_id = fields.Many2one(
        'de.student', 'Student',
        default=lambda self: self.env['de.student'].search(
            [('user_id', '=', self.env.user.id)]), required=True, ondelete="cascade")

    student_ids = fields.Many2many(
        'de.student', store=True, readonly=True, compute="_compute_student_ids")
    state = fields.Selection([
        ('draft', 'Draft'), ('reject', 'Rejected'), ('correcting', 'Correcting'),
        ('finish', 'Finished')], string='State',
        default='draft', tracking=True)
    mark = fields.Integer('Mark', tracking=True, readonly=True, store=True, compute="_compute_mark")
    answer_ids = fields.One2many('de.quiz.submission.answer', 'submission_id', 'Answers')
    attempt_ids = fields.Many2many('de.quiz.submission.attempt', string="Attempts", compute="_compute_attempt_ids",
                                   readonly=True, store=True)

    ## ???? why add these
    user_id = fields.Many2one(
        'res.users', related='student_id.user_id', string='User')
    teacher_user_id = fields.Many2one(
        'res.users', related='quiz_id.teacher_id.user_id',
        string='Teacher User')
    user_boolean = fields.Boolean(string='Check internal user',
                                  compute='_compute_user_boolean')
    is_quiz_user = fields.Boolean(string='Check quiz user',
                                  compute='_compute_is_quiz_user')

    @api.depends('quiz_id')
    def _compute_student_ids(self):
        for rec in self:
            students = rec.quiz_id.student_ids
            filtered_student = students.filtered(
                lambda student: self.check_student_submission(student, rec.quiz_id))
            rec.student_ids = filtered_student

    def check_student_submission(self, student, quiz):
        if student.quiz_submission_ids.filtered(lambda submission: submission.quiz_id.id == quiz.id):
            return False
        else:
            return True

    @api.depends('student_id', 'quiz_id.attempt_ids', 'quiz_id')
    def _compute_attempt_ids(self):
        for rec in self:
            rec.attempt_ids = self.env['de.quiz.submission.attempt'].search(
                [('student_id', '=', rec.student_id.id), ('quiz_id', '=', rec.quiz_id.id)]).ids

    @api.depends('quiz_id', 'answer_ids')
    def _compute_mark(self):
        for rec in self:
            result = 0
            for answer in rec.answer_ids:
                if answer.is_correct or answer.consider_correct:
                    result += answer.mark
            rec.mark = result

    def set_draft(self):
        self.state = 'draft'

    def set_finish(self):
        self.state = 'finish'

    def set_reject(self):
        self.state = 'reject'

    def set_correcting(self):
        self.state = 'correcting'

    @api.model_create_multi
    def create(self, vals):
        if self.env.user.child_ids:
            raise Warning(_('Parent cant submit student quiz!'))
        return super(DeQuizSubmission, self).create(vals)

    def write(self, vals):
        if self.env.user.child_ids:
            raise Warning(_('Parent cant submit student quiz!'))
        return super(DeQuizSubmission, self).write(vals)



    @api.depends('quiz_id', 'student_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.quiz_id.name} - {rec.student_id.name}"

    @api.model
    def create(self, vals):
        res = super(DeQuizSubmission, self).create(vals)
        for rec in res:
            for question in res.quiz_id.question_ids:
                rec.answer_ids.create({'submission_id': rec.id, 'question_id': question.id})
        return res

    def unlink(self):
        for rec in self:
            rec.attempt_ids.unlink()
        return super(DeQuizSubmission, self).unlink()
