{
    "name": "Alkahf implementation",
    "version": "18.0.1.0.2",
    "depends": ["base","account" ,'l10n_ae','sale' , 'stock','dekad_real_estate','sh_pdc','hr_expense','purchase', 'mail','dekad_account_enhancement'],
    'description': """
        -- Add Discount Product support with automatic discount calculations and summaries on Sales Orders and Customer Invoices.

        -- enhance Customer Invoices with Sales Order references, read-only tax amounts, and customized Tax Invoice reports.
    
        -- Prevent Sales Order confirmation below product cost through configurable company settings.
    
        -- Generate customized Sales Quotations, Trading Quotations, Trading Tax Invoices, Delivery Slips, Rent Receipts, Commitment & Declaration forms, and Journal Entry reports.
    
        -- Configure company-specific document settings including Company Header, Watermark, Company Code, P.O. Box, Tax Invoice Terms, Commitment & Declaration Terms, and Sale Price validation settings.
    
        -- Manage Purchase Order document attachments.
    
        -- Generate sequential numbering for Expense Sheets and link Expenses to their corresponding Journal Entries.
    
        -- Add Trade License and Trade Name information to Contacts.
    
        -- Display total ordered and delivered quantities on Delivery Orders.

""",
    "data": [
        # 'data/res_company_data.xml',
        'security/ir.model.access.csv',
        'report/sale_commitment_report.xml',
        'report/sale_commitment_report_template.xml',
        # 'report/rent_receipt_template.xml',
        'report/account_move_report.xml',
        'report/account_move_tax_invoice.xml',
        'report/alkahaf_delivery_report.xml',
        'report/realestate_sale_order_template.xml',
        'report/trading_sale_order_template.xml',
        'report/trading_tax_invoice_template.xml',

        "views/report_journal_entries_view.xml",
        'views/sale_oder_line_view.xml',
        'views/res_company.xml',
        'views/res_partner_views.xml',
        'views/hr_expense_sheet_view.xml',
        'views/hr_expense_report.xml',
        'views/product_template_views.xml',
        'views/account_move_view.xml',
        "views/purchase_order_view.xml",
        "views/res_config_settings_views.xml",

    ],
    'assets': {
        'web.assets_backend': [
            'alkahf_implementation/static/src/xml/tax_totals_readonly.xml',
        ],
    },
    "application": False,
    "installable": True,
}
