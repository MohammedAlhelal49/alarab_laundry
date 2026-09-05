# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Dekad Employees in Gantt',
    'category': 'Hidden',
    'summary': 'Dekad Employees in Gantt',
    'version': '1.0',
    'description': """ """,
    'depends': ['hr', 'web_gantt'],
    'auto_install': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend_lazy': [
            'hr_gantt/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'hr_gantt/static/tests/**/*',
        ],
    }
}
