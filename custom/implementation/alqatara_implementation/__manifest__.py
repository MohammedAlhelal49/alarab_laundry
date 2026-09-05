# -*- coding: utf-8 -*-
{
    'name': 'Alqatara Implementation',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Custom implementation for Alqattara ',
    'description': """

- Adds List View to Time Off Analysis by Employee and Time Off Type report.
""",
    'author': 'DSS',
    'depends': ['hr_holidays','sale_management','analytic', 'account', 'mail','sale'],
    'data': [
        'security/security_groups.xml',
        'views/hr_leave_report_views.xml',
        'views/sale_order_views.xml',

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}