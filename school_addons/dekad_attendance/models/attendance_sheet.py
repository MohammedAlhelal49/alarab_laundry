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


class DeAttendanceSheet(models.Model):
    _name = "de.attendance.sheet"
    _inherit = ["mail.thread"]
    _description = "Attendance Sheet"
    _order = "grade_id,classroom_id,attendance_date desc"

    @api.depends('classroom_id', 'attendance_date')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.classroom_id.name} - {rec.attendance_date}"

    sequence = fields.Char('Sequence', readonly=True, store=True, copy=False,
                           default=lambda self: self.env['ir.sequence'].next_by_code('de.attendance.sheet'))

    classroom_id = fields.Many2one(
        'de.classroom', 'Classroom', ondelete="cascade")

    grade_id = fields.Many2one(
        'de.grade', string="Grade", related="classroom_id.grade_id", readonly=True, store=True)

    attendance_date = fields.Date(readonly=True, store=True,
                                  default=lambda self: fields.Date.today(),
                                  tracking=True)

    attendance_line_ids = fields.One2many(
        'de.attendance.line', 'attendance_sheet_id', 'Student attendance')

    #  the count fields
    total_student_count = fields.Integer(compute='compute_total_student_count', string="Attendees")
    total_present_student_count = fields.Integer(compute='compute_total_present_student_count',
                                                 string="Total present students")
    total_absent_student_count = fields.Integer(compute='compute_total_absent_student_count',
                                                string="Total absent students")
    total_leave_student_count = fields.Integer(compute='compute_total_leave_student_count',
                                               string="Total Leave students")

    @api.model
    def search(self, args, offset=0, limit=None, order=None):

        if self.env.user.has_group('dekad_core.group_de_teacher'):
            last_week = datetime.now() - timedelta(days=7)
            args.append(('attendance_date', '>=', last_week.strftime('%Y-%m-%d')))
        return super(DeAttendanceSheet, self).search(args, offset, limit, order)

    def has_leave(self, student):
        has_leave = False
        for leave in student.leave_ids:
            if (leave.start_date == fields.Date.today() or leave.end_date == fields.Date.today() or (
                    leave.start_date < fields.Date.today() < leave.end_date)) and leave.state == 'accept':
                has_leave = True
        return has_leave

    @api.model_create_multi
    def create(self, vals):
        res = super(DeAttendanceSheet, self).create(vals)
        students = res.classroom_id.student_ids
        objects = []
        dict = {}

        for student in students:
            dict['student_id'] = student.id
            dict['attendance_sheet_id'] = res.id
            dict['leave'] = self.has_leave(student)
            dict['present'] = not self.has_leave(student)
            objects.append(dict)
            dict = {}
        self.env['de.attendance.line'].create(objects)
        return res

    @api.depends('attendance_line_ids')
    def compute_total_student_count(self):
        for record in self:
            record.total_student_count = len(record.attendance_line_ids)

    @api.depends('attendance_line_ids')
    def compute_total_absent_student_count(self):
        for record in self:
            record.total_absent_student_count = len(record.attendance_line_ids.filtered(lambda item: item.absent))

    @api.depends('attendance_line_ids')
    def compute_total_leave_student_count(self):
        for record in self:
            record.total_leave_student_count = len(record.attendance_line_ids.filtered(lambda item: item.leave))

    @api.depends('attendance_line_ids')
    def compute_total_present_student_count(self):
        for record in self:
            record.total_present_student_count = len(record.attendance_line_ids.filtered(lambda item: item.present))

    def action_show_line(self):
        action = self.env.ref('dekad_attendance.act_open_de_attendance_line_view').read()[0]
        action['domain'] = [('attendance_sheet_id', '=', self.id)]
        return action

    def cron_create_attendance_sheet(self):
        for record in self.env['de.classroom'].search([]):
            if not (record.attendance_sheet_ids and record.attendance_sheet_ids.filtered(
                    lambda sheet: sheet.attendance_date == fields.Date.today())) and record.student_ids:
                if not self.is_holiday():
                    dict = {}
                    dict['classroom_id'] = record.id
                    self.env['de.attendance.sheet'].create(dict)

    def is_holiday(self):
        is_holiday = False
        holidays = self.env['de.holiday'].search([])
        for holiday in holidays:
            if holiday.is_range:
                if holiday.start_date == fields.Date.today() or holiday.end_date == fields.Date.today() or (
                        holiday.start_date < fields.Date.today() < holiday.end_date):
                    is_holiday = True
            else:
                if holiday.date == fields.Date.today():
                    is_holiday = True

        return is_holiday

    @api.depends('classroom_id', 'attendance_date')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.classroom_id.display_name} - {rec.attendance_date}"
