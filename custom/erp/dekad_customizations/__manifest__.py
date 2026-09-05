{
    "name": "DEKAD Customizations",
    "version": "1.0.0",
    'summary': 'Custom report layouts and configurable properties for DEKAD',
    "description": """
    - Adds dynamic and configurable Properties fields to Contacts, Sales Orders,
        Purchase Orders, Invoices, Journal Entries, and Expenses using Odoo's
        standard Properties framework.
        
     - Provides a bilingual Arabic/English Odoo report layout with company details, a centered logo, translation support, and Document Layout configurator compatibility.
     - Use an uploaded image as report header/footer instead of the default text layout
    """,
    "depends": [
        "base",
        "contacts",
        "web",
        "sale",
        "account",
        "purchase",
        "hr_expense",

    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/purchase_order_views.xml",
        "views/hr_expense_views.xml",
        'views/base_document_layout_views.xml',
        'views/report_templates.xml',
        'report/report_layout_templates.xml',
        'data/report_layout.xml',
        "views/report_properties.xml",

    ],
    'assets': {
        'web.report_assets_common': [
            'dekad_customizations/static/src/scss/bilingual_report.scss',
        ],
    },

    "installable": True,
    "application": False,
    "license": "LGPL-3",
}