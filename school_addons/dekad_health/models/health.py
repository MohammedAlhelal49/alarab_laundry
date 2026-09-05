# -*- coding: utf-8 -*-
###############################################################################
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2009-TODAY Tech-Receptives(<http://www.techreceptives.com>).
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

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DeHealth(models.Model):
    _name = 'de.health'
    _description = """Medical information"""

    height = fields.Integer('Height(C.M.)')
    weight = fields.Integer('Weight')
    blood_group = fields.Selection(
        [('A+', 'A+ve'), ('B+', 'B+ve'), ('O+', 'O+ve'), ('AB+', 'AB+ve'),
         ('A-', 'A-ve'), ('B-', 'B-ve'), ('O-', 'O-ve'), ('AB-', 'AB-ve')],
        'Blood Type')
    physical_challenge = fields.Boolean('Physical Disability?')
    physical_challenge_note = fields.Text('Physical Disability notes')
    major_disease = fields.Boolean('Serious Illness?')
    major_disease_note = fields.Text('Serious Illness notes')
    eye_glasses = fields.Boolean('Vision problems?')
    eye_glasses_note = fields.Char('Vision problems notes')

    type = fields.Selection(
        [('student', 'Student'), ('teacher', 'Teacher'),
         ],
        'For', required=True, default='student')
    student_id = fields.Many2one('de.student', 'Student', ondelete="cascade")
    student_image = fields.Image('Image', store=True, readonly=True, compute="_compute_student_image")

    teacher_id = fields.Many2one('de.teacher', 'Teacher', ondelete="cascade")
    teacher_image = fields.Image('Image', store=True, readonly=True, compute="_compute_teacher_image")

    @api.constrains('height', 'weight')
    def check_height_weight(self):
        if self.height < 0.0 or self.weight < 0.0:
            raise ValidationError("Enter proper height and weight!")

    @api.depends('student_id', 'student_id.image_1920')
    def _compute_student_image(self):
        for rec in self:
            rec.student_image = rec.student_id.image_1920 if rec.student_id else False

    @api.depends('teacher_id', 'teacher_id.image_1920')
    def _compute_teacher_image(self):
        for rec in self:
            rec.teacher_image = rec.teacher_id.image_1920 if rec.teacher_id else False

    @api.depends('student_id', 'teacher_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.student_id.name if rec.student_id else rec.teacher_id.name}"
