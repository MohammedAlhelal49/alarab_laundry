# -*- coding: utf-8 -*-
{
    'name': 'PDC Payment Follow-up Management',
    'version': '1.2',
    'category': 'Accounting/Accounting',
    'description': 'Mirrors account_followup exactly, applied to PDC cheques.',
    'depends': ['sh_pdc', 'account_followup', 'mail', 'sms'],
    'data': [
        'security/pdc_followup_security.xml',
        'security/ir.model.access.csv',
        'security/sms_security.xml',
        'data/pdc_followup_data.xml',
        'data/cron.xml',
        'wizard/followup_manual_reminder_views.xml',
        'wizard/followup_missing_information.xml',
        'views/pdc_followup_line_views.xml',
        'views/pdc_followup_views.xml',
        'views/partner_view.xml',
        'views/report_followup.xml',
        'views/res_config_settings_view.xml',

    ],
    'post_init_hook': 'disable_pdc_followup_feature',

    'installable': True,
    'license': 'LGPL-3',
}
