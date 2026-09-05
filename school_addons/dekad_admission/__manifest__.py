{
    'name': "Dekad Admission",
    'version': '18.0',
    'license': 'LGPL-3',
    'category': 'Education',
    'sequence': 3,
    'summary': "Manage Admissions""",
    'author': 'Dekad',
    'depends': [
        'dekad_core',
        'dekad_fee',
        'account',
        'dekad_classroom',
    ],
    'data': [
        'security/ir_rule_data.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/admission_view.xml',
        'views/grade_view.xml',
        'report/admission_analysis_report.xml',
        'wizard/admission_analysis_wizard_view.xml',
        'wizard/multi_admission_wizard.xml',
        'menus/menu.xml',
    ],

    'application': True,
}
