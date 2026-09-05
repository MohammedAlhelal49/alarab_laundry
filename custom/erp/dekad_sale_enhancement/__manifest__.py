{
    "name": "Dekad Sale enhancement",
    "summary": "Add additional features and enhancements to the sale app",
    'description': """
    *** Add Additional Features to the sale app ***
-- Add additional fields to the sale report

-- Add the ability to input the price include vat in the sale order form

-- Add Profit analysis per invoice in sales reports

-- Spreadsheet dashboard to monitor slow or inactive selling products

-- Allow sale user to create and show his customers payments

-- Configurable limit sale user sale order confirmation based on unvalidated deliveries count

-- Add the ability to send whatsapp message to customer from the sale order

-- Add the feature to restrict confirming a sale order if its amount exceded a configurable field 

-- Add a company configurable feature to automatically validate the delivery transfer and create , post the generated invoice on the sale order confirmation 

-- Restrict Sales and CRM document access by allowing users to view only their own and selected users' sales records, leads, and opportunities.

-- Transfer a user's CRM leads, opportunities, and contacts between companies from the Action (gear) menu.

-- Display line numbering on Sale Orders.

-- Add delivered amount and amount-to-deliver fields on Sale Order lines.

-- Add an Inactive (Never Sold) Products report.

-- Add default WhatsApp quotation templates with dynamic quotation placeholders.

-- Adds a printable PDF report to Sales Analysis.
""",
    "version": "18.0",
    "category": "Dekad/Customizations",
    "license": "LGPL-3",
    "installable": True,
    "depends": ["base", "sale","contacts", "crm", "sale_management","sales_team", "sale_stock", "account", "spreadsheet_dashboard_sale"  , "dekad_additional_features"],
    "data": [
        "security/ir.model.access.csv",
        "security/sale_selected_users_groups.xml",
        "security/sale_selected_users_rules.xml",
        "views/res_users_views.xml",
        "report/sale_report_views.xml",
        "report/custom_sale_order_report.xml",
        "data/spreadsheet_dashboard.xml",
        "data/qoutation_whatsapp_template.xml",
        "views/customer_payment_menus.xml",
        "views/sale_order_views.xml",
        "views/sale_order_report.xml",
        "views/whatsapp_template_views.xml",
        "views/res_config_settings_view.xml",
        "views/product_inactive_report_views.xml",
        "wizards/transfer_company_wizard_views.xml",

    ],

}
