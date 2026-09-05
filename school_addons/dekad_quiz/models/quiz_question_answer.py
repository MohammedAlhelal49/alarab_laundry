# -*- coding: utf-8 -*-
# Part of DencCode. See LICENSE file for full copyright & licensing details.

##############################################################################
#
#    DencCode Inc
#    Copyright (C) 2009-TODAY DencCode Inc(<http://www.dekad.org>).
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DeQuizQuestionAnswer(models.Model):
    _name = 'de.quiz.question.answer'
    _description = "quiz question answer"

    question_id = fields.Many2one('de.quiz.question', string="Question", required=True, ondelete="cascade")
    submission_answer_id = fields.Many2one('de.quiz.submission.answer', string="Quiz submission answer")
    name = fields.Char(string="Answer", required=True)
    is_correct = fields.Boolean('Is Correct', store=True)

    @api.depends('is_correct', 'name')
    def _compute_display_name(self):
        for rec in self:
            result = f" - (Right)" if rec.is_correct else ''
            rec.display_name = f"{rec.name}{result}"

    @api.constrains('name')
    def check_name(self):
        for rec in self:

            if rec.search_count([('name', '=', rec.name), ('question_id', '=', rec.question_id.id)]) > 1:
                raise ValidationError(_(
                    f"Name must be unique per question answer"))
