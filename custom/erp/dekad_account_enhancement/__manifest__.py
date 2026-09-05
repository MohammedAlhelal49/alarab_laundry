# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017-2018 Tecnativa - Jairo Llopis
# Copyright 2018-2019 Tecnativa - Alexandre Díaz
# Copyright 2021 ITerra - Sergey Shebanin
# Copyright 2023 Onestein - Anjeel Haria
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Dekad Account Enhancment",
    "summary": "Add Additional Features to account section ",
    "description": """

    -- Add server actions to Cancel and Reset to Draft multiple Invoices, Bills, Journal Entries and Payments.

    -- Add a Force Reset to Draft server action for Account Moves with an indicator showing entries that were force reset.

    -- Automatically update the Journal Entry sequence when the accounting date changes and notify users when the entry number is updated.

    -- Limit customer invoicing based on the customer's credit limit with a permission-based override.

    -- Prevent posting Journal Entries that would create a negative balance for selected accounts.

    -- Add an optional Company column to the General Ledger and Partner Ledger reports.

    -- Automatically assign the selected Analytic Account and Analytic Distribution to Payment Journal Entries.

    -- Create, confirm and validate Return Deliveries directly from Customer Credit Notes, with an optional setting to enable or disable the feature.

    -- Add a smart button to view related Return Pickings from Customer Invoices.

    -- Add automatic line numbering for Invoice Lines, Journal Items and Expense Lines with manual sequencing support for Expense Lines.

    -- Increase the editable list limit for Invoice Lines and Journal Items.
    
    -- Adds per-journal sequence date formatting (No Date, Year, or Year & Month) and a journal-specific resequence action for posted journal entries.

    -- Apply discounts on Customer Invoices and Vendor Bills
    
    -- Adds a printable PDF Customer Invoice summary report with totals.'
    -- Set a company-level default customer that auto-fills on new Customer Invoices
    -- Redirect credit note income lines to a dedicated refund account
""",
    "version": "18.0",
    "category": "Dekad/Customizations",
    "author": "Dekad software solutions",
    "license": "LGPL-3",
    "installable": True,
    "depends": ["account", "base", "web","hr_expense","stock","sale"],
    "data": [
        "security/ir_rule_data.xml",
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'data/product_data.xml',
        'wizard/account_invoice_discount_views.xml',
        "views/account_move_views.xml",
        'views/account_payment_views.xml',
        "views/account_move_line_views.xml",
        "views/hr_expense_views.xml",
        "views/res_config_settings_views.xml",
        "views/account_journal_views.xml",
        "views/account_move_line_report.xml",
        "report/custom_invoice_report.xml",
    ],
}
