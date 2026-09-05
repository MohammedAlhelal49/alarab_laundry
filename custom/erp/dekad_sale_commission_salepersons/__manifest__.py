# -*- coding: utf-8 -*-
{
    "name": "Dekad Sale Additional Salesperson",
    "version": "18.0.1.0.0",
    "description": '''
 - Adds support for assigning multiple salespersons to Sale Orders in addition to the primary salesperson.
 - Automatically copies additional salespersons from Sale Orders to Customer Invoices.
 - Displays additional salespersons in Sale Order and Invoice form and list views using avatar widgets.
 - Extends Sales Commission calculations to include both primary and additional invoice salespersons.
 - Splits net paid commission amounts equally across all invoice participants.
 - Calculates and displays paid amount, third-party deductions, tax deduction, net paid, and net paid after split.
 - Introduces configurable commission deductions based on Journal Payment Method Lines and applies them automatically during invoice commission calculations.
 - Adds approval and unapproval actions to commission achievement reports, freezes approved records using snapshots to prevent recalculation, and visually distinguishes approved rows in reports.
 - Restricts commission menus and configuration access based on Sales user roles.
 ''',
    "summary": "Adds an Additional Salesperson field to Sale Orders with same behavior as Salesperson.",
    "license": "LGPL-3",
    "depends": ["sale_management", "sales_team", "sale", "sale_commission", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/payment_method_deduction_views.xml",
        "views/sale_order_views.xml",
        'views/sale_achievement_report_views.xml',
        "views/menu_overrides.xml",
    ],
    "application": False,
    "installable": True,
}
