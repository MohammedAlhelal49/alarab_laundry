{
    'name': 'Dekad HR Paid Leave Allowance',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Wizard to manage Paid Leave Allowance within remaining limits',
    'depends': ['hr_holidays','hr_contract','base','l10n_ae_hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/paid_leave_allowance_wizard_view.xml',
        'views/paid_leave_allowance_log_view.xml',
        'views/hr_contract_view.xml',
        'views/menu.xml',

    ],
    'installable': True,
    'application': False,
}
