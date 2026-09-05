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
    'name': 'Dekad Fee',
    'version': '18.0',
    'license': 'LGPL-3',
    'category': 'Education',
    "sequence": 3,
    'summary': 'Manage Fees',
    'author': 'Dekad',
    'depends': ['base', 'dekad_core', 'account'],
    'data': [
        'security/ir_rule_data.xml',
        'security/ir.model.access.csv',
        'views/fee_term_view.xml',
        'views/student_view.xml',
        'views/grade_view.xml',
        'views/student_fee_view.xml',
        'report/student_fee_report.xml',
        'menus/menu.xml',
        # 'menus/menu.xml',
        'website/main.xml',

    ],

    'application': True,
}
