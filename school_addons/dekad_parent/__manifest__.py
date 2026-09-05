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
    'name': 'Dekad Parent',
    'version': '18.0',
    'license': 'LGPL-3',
    'category': 'Education',
    "sequence": 3,
    'summary': 'Manage Parent',
    'complexity': "eaDe",
    'author': 'dekad',
    'depends': ['base', 'dekad_core'],
    'data': [
        'security/ir_rule_data.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/ir_sequence_data.xml',
        'views/parent_view.xml',
        'views/student_view.xml',
        'views/parent_relationship_view.xml',
        'wizard/parent_create_user_wizard_view.xml',
        'report/parent_idcard_report.xml',
        'menus/menu.xml',
        'website/main.xml',
        # demo records
       #  'demo/de_parent.xml',

    ],
    'application': True,
}
