{
    'name': 'Al Omran CRM Enhancements',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'Enhances CRM by preventing duplicates and automating opportunity reassignment',
    'depends': ['crm','base','sale','web' , 'contacts','dekad_sale_enhancement','utm'],
    'data': [
        'security/ir.model.access.csv',
        'data/crm_cron.xml',
        'data/schedule_day_data.xml',
        'data/course_duration_units_data.xml',
        'data/utm_sources.xml',
        'views/sale_report_inherit.xml',
        'views/crm_settings_view.xml',
        'views/res_partner_views.xml',
        'views/sale_order_view.xml',
        'views/sale_report_view.xml',
        "views/res_users_views.xml",
        "wizard/transfer_company_wizard_views.xml",

    ],
    'assets': {
        'web.assets_frontend': [
            'alomran_implementation/static/src/js/patch_signature.js',
            'alomran_implementation/static/src/css/hide_auto_button.css',

        ],
        "web.assets_backend": [
            "alomran_implementation/static/src/js/list_confirmation_dialog_patch.js",
            "alomran_implementation/static/src/js/takeover_button.js",
            "alomran_implementation/static/xml/takeover_button.xml",
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'description': '''
- Prevents duplicate CRM opportunities for the same customer with the same title.
- Supports configurable duplicate contact handling (Warning Only or Prevent Duplicates) from Settings.
- Blocks creation or modification of contacts with duplicate names or phone/mobile numbers when duplicate prevention is enabled.
- Displays duplicate contact warnings (Name and Phone/Mobile) on both the Contacts form and the CRM Opportunity form.
- Synchronizes the CRM Opportunity mobile number with the linked Contact (res.partner) when edited.
- Adds settings to enable automatic opportunity transfer after a configurable duration (in days).
- Automatically reassigns stale opportunities to a random salesperson using a daily cron job.
- Logs the salesperson transfer in the CRM chatter history for traceability.
- Extends the Contacts form by adding personal information fields and a read-only contract date set to the creation date.
- Adds custom course and enrollment fields to Sales Orders, and a read-only contract date set to the order creation date.
- Shows the mobile number in the partner display name instead of the address.
- Hides the Auto Signature button in the Sign interface.
- Transfers salesperson leads and contacts to another company.
''',

}



