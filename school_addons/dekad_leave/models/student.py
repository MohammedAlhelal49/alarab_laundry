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

from odoo import models, fields


class DeStudent(models.Model):
    _inherit = "de.student"

    leave_ids = fields.One2many('de.leave', 'student_id', string='Leaves')
    leave_count = fields.Integer(compute='compute_leave_count')

    def action_show_leave(self):
        action = self.env.ref('dekad_leave.'
                              'act_open_de_leave_view').read()[0]
        action['domain'] = [('student_id', '=', self.id)]
        return action

    def compute_leave_count(self):
        for record in self:
            record.leave_count = len(record.leave_ids)
