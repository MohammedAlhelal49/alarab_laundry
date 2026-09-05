# -*- coding: utf-8 -*-
{
    'name': "Contraventions",
    'summary': """ Contraventions""",
    'description': """   Contraventions """,
    'author': "Dekad Software Solutions",
    'license': 'LGPL-3',
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Education',
    'version': '18.0',
    'sequence':'1',
    # any module necessary for this one to work correctly
    'depends': ['dekad_parent', 'dekad_core', 'base', 'mail'],

    # always loaded
    'data': [
        'security/ir_rule_data.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/category_view.xml',
        'views/student_penalty_view.xml',
        'views/student_suspend_view.xml',
        'wizard/contravention_take_action_wizard_view.xml',
        'wizard/contravention_change_penalty_wizard_view.xml',
        'views/contravention_view.xml',
        'views/student_view.xml',
        'report/student_contravention_report.xml',
        'menus/menu.xml',
        # website,
        'website/main.xml',
    ],

}
