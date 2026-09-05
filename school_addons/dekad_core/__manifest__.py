# -*- coding: utf-8 -*-
###############################################################################
#
#    dekad Inc
#    Copyright (C) 2009-TODAY dekad Inc(<http://www.dekad.org>).
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
    'name': 'dekad Core',
    'version': '18.0',
    'license': 'LGPL-3',
    'category': 'Website',
    "sequence": 1,
    'summary': 'Manage Students, Teachers and Education Institute',
    'author': 'dekad',
    'depends': ['base', 'mail', 'portal', 'hr'],
    'data': [
        'security/ir_rule_data.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/religion_view.xml',
        'views/holiday_view.xml',
        'views/student_view.xml',
        'views/grade_view.xml',
        'views/subject_view.xml',
        'views/specialist_view.xml',
        'views/teacher_view.xml',
        'views/student_grade_view.xml',
        'views/hr_employee_view_inherited.xml',
        'views/academic_year_view.xml',
        'views/academic_term_view.xml',
        'wizard/teacher_create_user_wizard_view.xml',
        'wizard/student_create_user_wizard_view.xml',
        'wizard/student_grade_wizard_view.xml',
        # reports section
        'report/student_idcard_report.xml',
        'report/teacher_idcard_report.xml',
        'report/menu.xml',
        # # reports section
        'menus/school_menu.xml',
        'menus/teacher_menu.xml',
        'menus/student_menu.xml',
        # website
        'website/main.xml',
        # # demo records
        # 'demo/de_academic_year.xml',
        # 'demo/de_academic_term.xml',
        # 'demo/de_religion.xml',
        # 'demo/de_holiday.xml',
        # 'demo/de_grade.xml',
        # 'demo/de_specialist.xml',
        # 'demo/de_teacher.xml',
        # 'demo/de_student.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': True,

}
