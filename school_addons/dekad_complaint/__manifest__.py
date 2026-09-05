# -*- coding: utf-8 -*-
{
    'name': "Complaints",
    'summary': """Complaints manage""",
    'description': """Complaints manage""",
    'author': "Dekad Software Solutions",
    'license': 'LGPL-3',
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Education',
    'version': '18.0',
    'sequence': 3,
    # any module necessary for this one to work correctly
    'depends': ['dekad_core', 'base', 'mail', 'dekad_parent'],
    # always loaded
    'data': [
        'security/ir_rule_data.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/complaint_category_view.xml',
        'views/complaint_view.xml',
        'report/complaint_analysis_report.xml',
        'wizard/complaint_analysis_wizard_view.xml',
        'menus/menu.xml',
        # website
        'website/main.xml',
    ],
}
