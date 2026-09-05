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
    'name': 'Dekad Assignment',
    'version': '18.0',
    'license': 'LGPL-3',
    'category': 'Education',
    "sequence": 3,
    'summary': 'Manage Assgiments',
    'complexity': "eaDe",
    'author': 'DencCode Inc',
    'website': 'http://www.dekad.org',
    'depends': [
        'dekad_core','dekad_classroom','dekad_admission'
    ],
    'data': [
        'security/ir_rule_data.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/assignment_type_view.xml',
        'views/assignment_view.xml',
        'views/assignment_submission_view.xml',
        'views/student_view.xml',
        'views/grade_view.xml',
        'views/teacher_view.xml',
        'menus/menu.xml',
        # 'views/subject_view.xml',
        # website',
        'website/main.xml',
    ],
    'images': [
        'static/description/dekad_assignment_banner.jpg',
    ],

    'application': True,
}
