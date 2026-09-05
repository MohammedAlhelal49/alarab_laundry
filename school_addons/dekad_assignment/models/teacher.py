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

from odoo import models, fields, api


class DeTeacher(models.Model):
    _inherit = "de.teacher"

    assignment_ids = fields.One2many('de.assignment', 'teacher_id', string='Assignment(s)')
    assignment_count = fields.Integer(compute='_compute_assignment_count')

    @api.depends('assignment_ids')
    def _compute_assignment_count(self):
        for record in self:
            record.assignment_count = len(record.assignment_ids)

    def action_show_assignment(self):
        action = self.env.ref('dekad_assignment.act_open_de_assignment_view').read()[0]
        action['domain'] = [('teacher_id', '=', self.id)]
        return action
