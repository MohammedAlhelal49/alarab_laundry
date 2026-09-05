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


class DeQuizSubmissionAnswer(models.Model):
    _name = "de.quiz.submission.answer"
    _rec_name = "submission_id"
    _description = "quiz Submission answer"
    _order = "submission_id"

    def _compute_is_quiz_user(self):
        for user in self:
            if self.env.user.has_group('dekad_quiz.group_de_quiz'):
                user.is_quiz_user = True
            else:
                user.is_quiz_user = False

    submission_id = fields.Many2one(
        'de.quiz.submission', 'Submission', required=True, ondelete="cascade")
    question_id = fields.Many2one(
        'de.quiz.question', 'Question', required=True, ondelete="cascade")
    answer = fields.Char('Answer')
    is_correct = fields.Boolean('Is correct', compute='_compute_is_correct', readonly=True, store=True)
    mark = fields.Integer(string='Mark', related='question_id.mark', readonly=True, store=True)

    question_type = fields.Selection([('descriptive', 'Descriptive'), ('select_from_multiple', 'Select from multiple')
                                      ], string="Question Type", related="question_id.type", readonly=True,
                                     store=True)

    right_answer = fields.Char(' Right Answer', related="question_id.answer", readonly=True, store=True)
    answer_ids = fields.One2many('de.quiz.question.answer', 'submission_answer_id', related="question_id.answer_ids",
                                 readonly=True,
                                 store=True, string="Question options")

    is_quiz_user = fields.Boolean(string='Check quiz user',
                                  compute='_compute_is_quiz_user')
    consider_correct = fields.Boolean("Consider the answer right ?")
    gained_mark = fields.Integer(string='Gained mark', compute='_compute_gained_mark', readonly=True, store=True)

    @api.depends('mark', 'is_correct', 'consider_correct')
    def _compute_gained_mark(self):
        for rec in self:
            rec.gained_mark = rec.mark if (rec.is_correct or rec.consider_correct) else 0

    @api.depends('answer', 'question_id.answer', 'question_id.type',
                 'question_id.answer_ids')
    def _compute_is_correct(self):
        for rec in self:
            rec.is_correct = (rec.answer == rec.question_id.answer) if rec.question_type == 'descriptive' else (
                    rec.answer == rec.question_id.answer_ids.filtered(lambda r: r.is_correct)[0].name)
