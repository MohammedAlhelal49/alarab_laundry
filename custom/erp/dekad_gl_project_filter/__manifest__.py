# -*- coding: utf-8 -*-
{
    'name': 'Dekad GL Project & Task Filter',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Filter General Ledger by Project and Tasks',
    'description': """
        Adds Project and Task filters to the General Ledger report.

        - Project filter: scopes all journal lines to a selected project
          (matches on account.move.project_id, provided by dekad_construction).
        - Task filter: further scopes to one or more tasks within that project
          (matches on account.move.line.task_id, provided by dekad_construction).

        Both filters are injected only on General Ledger via
        AccountGeneralLedgerReportHandler._custom_options_initializer.
        All other reports are unaffected.

        Requires: dekad_construction (provides project_id / task_id fields
        on account.move and account.move.line).
    """,
    'author': 'Dekad',
    'depends': [
        'account_reports',
        'dekad_construction',
    ],
    'assets': {
        'web.assets_backend': [
            'dekad_gl_project_filter/static/src/components/project_filter.js',
            'dekad_gl_project_filter/static/src/components/project_filter.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
}
