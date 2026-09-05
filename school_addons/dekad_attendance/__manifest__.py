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

{
    'name': 'Dekad Attendance',
    'version': '18.0',
    'license': 'LGPL-3',
    'category': 'Education',
    "sequence": 3,
    'summary': 'Manage Attendances',
    'complexity': "eaDe",
    'author': 'Dekad Inc',
    'website': 'http://www.dekad.org',
    'depends': ['dekad_core', 'dekad_classroom'],
    'data': [
        'security/ir_rule_data.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/ir_sequence_data.xml',
        'views/attendance_sheet_view.xml',
        'views/attendance_line_view.xml',
        'views/student_view.xml',
        'report/attendance_analysis_report.xml',
        'wizard/attendance_analysis_wizard_view.xml',
        'menus/menu.xml',
        # 'menus/menu.xml',
        'website/main.xml',
    ],
    'images': [
        'static/description/dekad_attendance_banner.jpg',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
