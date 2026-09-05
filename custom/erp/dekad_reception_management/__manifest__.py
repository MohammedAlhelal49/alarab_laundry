# -*- coding: utf-8 -*-
{
    'name': 'Reception Management',
    'version': '18.0.1.0.0',
    'category': 'Sales/Front Desk',
    'summary': 'Simplified front-desk app: Customers, Invoices and Customer Payments',
    'author': 'DSS',
    'license': 'LGPL-3',
    'depends': [
        'account',
    ],
    'data': [
        'security/reception_security.xml',
        'security/ir.model.access.csv',
        'views/reception_menus.xml',
    ],
    'application': True,
    'installable': True,
}
