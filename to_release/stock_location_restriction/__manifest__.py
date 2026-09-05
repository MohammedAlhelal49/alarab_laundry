# -*- coding: utf-8 -*-
{
    'name': 'Barada Stock Location Restriction',
    'version': '18.0.1.0.0',
    'summary': 'Restrict stock locations visibility per user',
    'description': """
        Adds user-level access restriction on stock locations.
        - Add is_restricted flag on stock.location (visible to Administrator only)
        - Add allowed_user_ids Many2many field (visible to Administrator only)
        - Record Rule: location visible only to allowed users when restricted
    """,
    'author': 'Dekad',
    'category': 'Inventory/Inventory',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/stock_location_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
