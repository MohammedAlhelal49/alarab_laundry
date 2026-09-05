{
    'name': 'Ten Bridge Implementation',
    'version': '18.0.1.0.0',
    'category': 'Real Estate',
    'author': 'DSS',
    'depends': [
        'sale_management',
        'account',
        'dekad_real_estate',
    ],
    'description': """
    -- Extend Real Estate properties with Municipality, Area, Property Reference, Unit Reference, Property Code, Basin, Plot Number, and Property Usage information.

    -- Enhance Rental Contracts with Other Charges, Previous Contract references, Guarantee Cheques, Discount calculations, and Rental payment tracking.

    -- Generate customized Rental Contract Summary, Tenant Data Card, Payment Receipt, PDC, and PM Invoice reports.

    -- Display rental duration, payment schedules, Warranty Cheques, and amounts in words on Rental Contract reports.

    -- Add Discount Product support with automatic discount calculations for Rental Contracts.

    -- Automatically simplify Rental Contract numbering by removing generated prefixes.

    -- Add Arabic Company Name and Arabic Contact information, including Trade License, Trade Name, Fax, and P.O. Box.

    -- Customize company report layouts for Real Estate documents.
    
    --Hides the Rental Contract Availability and Contract Report menus (Real Estate).

""",
    'data': [
        "security/ir.model.access.csv",

        'report/tenant_data_card_template.xml',
        'report/rental_contract_summary_template.xml',
        'report/pm_invoice_template.xml',
        'report/pdc_wizard_template.xml',
        'report/payment_receipt.xml',

        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'views/analytic_account_view.xml',
        'views/res_company.xml',
        'views/product_template_views.xml',
        'views/report_layout.xml',
        'views/menu_override.xml',

    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
