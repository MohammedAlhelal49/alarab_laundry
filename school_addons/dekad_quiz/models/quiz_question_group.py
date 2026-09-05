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


class DeQuizQuestionGroupType(models.Model):
    _name = 'de.quiz.question.group.type'
    _description = "quiz question group type"
    name = fields.Char(string="Name", required=True)
    group_ids = fields.One2many('de.quiz.question.group', "type_id", string="Questions Groups")

    @api.constrains('name')
    def check_name(self):
        if self.search_count([('name', '=', self.name)]) > 1:
            raise ValidationError(_(
                f"Name must be unique per question group type"))


class DeQuizQuestionGroup(models.Model):
    _name = 'de.quiz.question.group'
    _description = "quiz question group"
    _order = "type_id"
    type_id = fields.Many2one('de.quiz.question.group.type', string="Type", required=True)
    name = fields.Char(string="Name", required=True)
    quiz_ids = fields.Many2many('de.quiz', string="Quizzes")
    question_ids = fields.Many2many('de.quiz.question', string="Questions")
    group_ids = fields.Many2many('de.quiz.question.group', string="Type elated groups", compute='_compute_group_ids')

    @api.constrains('name')
    def check_name(self):
        if self.search_count([('name', '=', self.name), ('type_id', '=', self.type_id.id)]) > 1:
            raise ValidationError(_(
                f"Name must be unique per question group inside the question group type"))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = self.name + " (copy)"
        return super(DeQuizQuestionGroup, self).copy(default)

    @api.depends('type_id')
    def _compute_group_ids(self):
        for rec in self:
            if rec.type_id:
                rec.group_ids = rec.type_id.group_ids
            else:
                rec.group_ids = False
