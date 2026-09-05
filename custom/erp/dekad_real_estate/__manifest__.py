{
    'name': 'Real Estate',
    'version': '18.0.1.0.2',
    'category': 'Real Estate',
    'summary': 'Manage real estate properties',
    'author': 'DSS',
    'depends': ['base', 'product','sale_management', 'analytic','contacts', 'account','sale', 'sh_pdc'],
    "description": """    
        -- Manage buildings, properties, property types, orientations, images, documents, and detailed property information.
    
        -- Create and manage rental and property sale contracts with support for hourly, daily, monthly, and yearly rental periods.
    
        -- Prevent booking conflicts, validate rental dates, and automatically generate contract lines based on property products and rental events.
    
        -- Schedule rental events through Calendar, List, and Form views with support for multiple properties, event pricing, and availability planning.
    
        -- Track property availability, rental status, sold properties, utility meter readings, invoice status, and occupancy information.
    
        -- Generate receipt vouchers, automate invoice creation and reconciliation, and support direct payments, PDC payments, payment sequencing, and multiple payment categories.
    
        -- Manage rental cancellations with dedicated workflows including Refund, No Response, No Refund, and Early Checkout scenarios.
    
        -- Generate Building Statements, Property Availability Reports, Contract Reports, and advanced reporting wizards with filtering by building, property, tenant, and period.
    
        -- Configure rental and property sale features through company settings.
        
        -- Added a "Renew" button on confirmed rental contracts (only enabled once an invoice is posted) that creates a linked draft copy starting the day after the current contract ends, carrying over the same existing contract information.
        
        -- Added Close/Reopen functionality for rental contracts, with a status pill (In Progress / Churned / Renewed) and search filters.
    """,
    'data': [
        'data/analytic_plan_data.xml',
        'data/sale_order_cron.xml',
        'data/property_type_data.xml',
        'data/property_orientation.xml',
        'data/rental_close_reason_data.xml',

        'security/real_estate_security.xml',
        'security/real_estate_groups.xml',
        'security/ir.model.access.csv',

        'views/building_view.xml',
        'views/availability_report_views.xml',
        'views/property_rental_event_views.xml',
        'views/analytic_account_view.xml',
        'views/meters_view.xml',
        'views/contract_report_view.xml',
        'views/sale_order_view.xml',
        'views/availability_view.xml',
        'views/property_analytic_form.xml',
        'views/res_partner_views.xml',
        'views/building_statement_line_views.xml',
        'views/sales_contracts.xml',
        'views/res_config_settings_view.xml',
        'wizards/rental_cancel_wizard_view.xml',
        'views/account_payment_view.xml',
        'views/product_template_views.xml',
        'wizards/contract_report_wizard_view.xml',
        'wizards/building_statement_wizard_views.xml',
        'views/pdc_wizard_views.xml',
        'wizards/property_availability_wizard_views.xml',
        'wizards/rental_close_wizard_views.xml',

        'views/ir_menu.xml',

        'report/contract_report.xml',
        'report/building_statement_line_report.xml',
        'report/availability_report.xml',
        'report/property_availability_report.xml',

        'security/availability_report_security.xml',

    ],
    'post_init_hook': 'assign_real_estate_groups',

    'installable': True,
    'application': True,
}
