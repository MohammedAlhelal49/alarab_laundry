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


class DeAttendanceAnalysisWizard(models.TransientModel):
    _name = "de.attendance.analysis.wizard"
    _description = "Attendance analysis wizard"

    all_time = fields.Boolean("All the time")

    from_date = fields.Date(
        'From Date', default=lambda self: fields.Date.today())
    to_date = fields.Date(
        'To Date', default=lambda self: fields.Date.today())

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date:
                from_date = fields.Date.from_string(record.from_date)
                to_date = fields.Date.from_string(record.to_date)
                if to_date < from_date:
                    raise ValidationError(
                        _("To Date cannot be set before From Date."))

    def print_report(self):
        data = self.read(['from_date', 'to_date', 'all_time'])[0]
        data.update({'student_id': self.env.context.get('active_id', False)})

        return self.env.ref(
            'dekad_attendance.act_open_de_attendance_analysis_report_view') \
            .report_action(self, data=data)
