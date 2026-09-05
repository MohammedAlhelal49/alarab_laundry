# -*- coding: utf-8 -*-
{
    'name': 'Dekad Accounting Reports Enhanced',
    'version': '18.0.1.2.0',
    'category': 'Accounting/Accounting',
    'summary': 'Secondary currency filter + Analytic Account column + Group by Analytic for General Ledger',
    'description': """
        1. Secondary Currency Filter
           Adds a "Secondary Currency" filter to all accounting reports.
           Journal items in that currency use amount_currency; others use company currency.

        2. Show Analytic Account (General Ledger)
           Optional column showing the Analytic Account per AML line.
           Toggled via Options → "Show Analytic Account".

        3. Group by Analytic Account (General Ledger)
           Restructures the General Ledger as:
               Analytic Account (level 1)
                 └── Account   (level 2)
                       └── AML lines + Initial Balance (level 3)
           Lines with no analytic appear under "∅ No Analytic Account".
           Toggled via Options → "Group by Analytic Account".
    """,
    'author': 'Dekad',
    'depends': ['account_reports', 'analytic', 'account'],
    'data': [
        'views/pdf_filter_info.xml',
        'views/account_report_views.xml',
        'data/account_report_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dekad_accounting_reports_enhanced/static/src/components/filter_secondary_currency.js',
            'dekad_accounting_reports_enhanced/static/src/components/filter_secondary_currency.xml',
            'dekad_accounting_reports_enhanced/static/src/components/warnings/warnings.xml',
            'dekad_accounting_reports_enhanced/static/src/components/custom_filters.js',
            'dekad_accounting_reports_enhanced/static/src/components/custom_filters.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}