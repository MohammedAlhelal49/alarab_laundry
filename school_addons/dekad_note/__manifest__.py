# -*- coding: utf-8 -*-
{
    'name': "Notes",

    'summary': """
        Notes 
        """,

    'description': """
         Notes 
    """,

    'author': "Team",
    'website': "",
    'license': 'LGPL-3',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Education',
    'version': '18.0',

    # any module necessary for this one to work correctly
    'depends': ['dekad_core', 'mail', 'dekad_parent', 'base'],

    # always loaded
    'data': [
        'security/ir_rule_data.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/note_group_view.xml',
        'views/note_view.xml',
        'menus/menu.xml',
        # website
        'website/main.xml',

    ],
    'application': True,

}
