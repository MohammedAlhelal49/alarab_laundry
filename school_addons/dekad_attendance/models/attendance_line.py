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
from datetime import datetime, timedelta


class DeAttendanceLine(models.Model):
    _name = "de.attendance.line"
    _inherit = ["mail.thread"]
    _rec_name = "attendance_sheet_id"
    _description = "Attendance Lines"
    _order = "classroom_id,attendance_date desc"

    attendance_sheet_id = fields.Many2one(
        'de.attendance.sheet', 'Attendance Sheet', required=True,
        tracking=True, ondelete="cascade")

    student_id = fields.Many2one(
        'de.student', 'Student', required=True, tracking=True, ondelete="cascade")
    present = fields.Boolean(
        'Present', default=True, tracking=True)
    absent = fields.Boolean('Absent', tracking=True)
    leave = fields.Boolean('Leave', tracking=True)

    classroom_id = fields.Many2one(
        'de.classroom', 'Classroom',
        related='attendance_sheet_id.classroom_id', store=True,
        readonly=True)

    remark = fields.Char('Remark', size=256)
    attendance_date = fields.Date(
        'Date', related='attendance_sheet_id.attendance_date', store=True,
        readonly=True, tracking=True)

    _sql_constraints = [
        ('unique_attendance_sheet_student',
         'unique(attendance_sheet_id,student_id)',
         'Student must be unique per Attendance.'),
    ]

    @api.depends('classroom_id', 'attendance_date', 'student_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.classroom_id.display_name} - {rec.attendance_date} - {rec.student_id.name}"

    @api.onchange('present')
    def onchange_present(self):
        if self.present:
            self.absent = False
            self.leave = False

    @api.onchange('absent')
    def onchange_absent(self):
        if self.absent:
            self.present = False
            self.leave = False

    @api.onchange('leave')
    def onchange_leave(self):
        if self.leave:
            self.present = False
            self.absent = False

        # teacher can only see attendance line since 7 days

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        if self.env.user.has_group('dekad_core.group_de_teacher'):
            last_week = datetime.now() - timedelta(days=7)
            args.append(('attendance_sheet_id.attendance_date', '>=', last_week.strftime('%Y-%m-%d')))
        return super(DeAttendanceLine, self).search(args, offset, limit, order)

    # suspended student's state will be automatically absent with remark
    # @api.model
    # def create(self, vals):
    #     student = self.env['de.student'].browse(vals['student_id'])
    #     if student.is_suspended:
    #         vals['leave'] = False
    #         vals['present'] = False
    #         vals['absent'] = True
    #         vals['remark'] = 'Suspended'
    #     return super(DeAttendanceLine, self).create(vals)
