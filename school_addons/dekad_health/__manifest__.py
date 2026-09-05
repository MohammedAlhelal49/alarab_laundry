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

{
    'name': 'Health managment',
    'version': '18.0',
    'license': 'LGPL-3',
    'category': 'Education',
    "sequence": 3,
    'summary': 'Manage Health',
    'complexity': "eaDe",
    'description': """
        This module adds the feature of health in Denccode
    """,
    'author': 'Mohammed alhelal',
    'website': 'https://github.com/mfaisalcfa/odoo-addons',
    'depends': ['base', 'dekad_core'],
    'data': [
        'security/ir_rule_data.xml',
        'security/ir.model.access.csv',
        'views/student_health_checkup_view.xml',
        'views/teacher_health_checkup_view.xml',
        'views/student_health_view.xml',
        'views/teacher_health_view.xml',

        'menus/menu.xml',
        # website,
        'website/main.xml',

    ],

    'application': True,
}
