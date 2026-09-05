# -*- coding: utf-8 -*-
{
    "name": "Sale Additional Salesperson",
    "version": "18.0.1.0.0",
    "summary": "Adds an Additional Salesperson field to Sale Orders with same behavior as Salesperson.",
    "license": "LGPL-3",
    "depends": ["sale_management", "sales_team","sale", "sale_commission","account"],
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
