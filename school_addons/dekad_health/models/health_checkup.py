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

from odoo import models, fields


class DeHealthCheckup(models.Model):
    _name = 'de.health.checkup'
    _description = 'Medical checkups'
    type = fields.Selection(
        [('student', 'Student'), ('teacher', 'Teacher'),
         ],
        'For', required=True, default='student')
    student_id = fields.Many2one('de.student', 'Student', ondelete="cascade")
    teacher_id = fields.Many2one('de.teacher', 'Teacher', ondelete="cascade")
    name = fields.Char('Checkup Name', required=True)
    file = fields.Binary('Attachment', copy=False)
    file_name = fields.Char(string="File Name",
                            copy=False)  # Added by Ahmed
    recommendation = fields.Text('Checkup Recommendation')
