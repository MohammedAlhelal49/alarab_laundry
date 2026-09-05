# -*- coding: utf-8 -*-
# Part of DencCode. See LICENSE file for full copyright & licensing details.

##############################################################################
#
#    DencCode Inc
#    Copyright (C) 2009-TODAY DencCode Inc(<http://www.dekad.org>).
#
##############################################################################

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError


class DeQuizQuestion(models.Model):
    _name = 'de.quiz.question'
    _description = "quiz question"

    quiz_ids = fields.Many2many('de.quiz', string="Quizzes")
    group_ids = fields.Many2many('de.quiz.question.group', string="Groups")
    name = fields.Char(string="Name", required=True)
    mark = fields.Integer('Mark', required=True, default=1)
    answer = fields.Char(string="Answer")
    type = fields.Selection([('descriptive', 'Descriptive'), ('select_from_multiple', 'Select from multiple')
                             ],
                            string="Type", default="descriptive", required=True)
    answer_ids = fields.One2many('de.quiz.question.answer', 'question_id', 'Answers', copy=True)

    @api.constrains('name')
    def check_name(self):
        if self.search_count([('name', '=', self.name)]) > 1:
            raise ValidationError(_(
                f"Name must be unique per question"))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = self.name + " (copy)"
        return super(DeQuizQuestion, self).copy(default)

    @api.constrains('mark')
    def _check_mark(self):
        for rec in self:
            if rec.mark <= 0:
                raise exceptions.ValidationError(_("Please enter prober mark"))

    @api.constrains('answer_ids')
    def _check_answers(self):
        for rec in self:
            if rec.type == 'select_from_multiple' and not rec.answer_ids:
                raise exceptions.ValidationError(_("There must be answers to the Select from multiple question !"))
            if rec.type == 'select_from_multiple' and len(rec.answer_ids.filtered(lambda r: r.is_correct)) != 1:
                raise exceptions.ValidationError(_("There must be one right answer !"))

    @api.onchange('type')
    def _onchange_type(self):
        for rec in self:
            if rec.type == 'select_from_multiple':
                rec.answer = ""
            if rec.type == 'descriptive':
                rec.answer_ids.unlink()

    def unlink(self):
        for rec in self:
            quizzes = rec.quiz_ids
            for quiz in quizzes:
                quiz.mark -= rec.mark
        return super(DeQuizQuestion, self).unlink()
