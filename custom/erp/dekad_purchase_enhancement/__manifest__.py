# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017-2018 Tecnativa - Jairo Llopis
# Copyright 2018-2019 Tecnativa - Alexandre Díaz
# Copyright 2021 ITerra - Sergey Shebanin
# Copyright 2023 Onestein - Anjeel Haria
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Dekad Purchase enhancement",
    'summary': 'Add some enhancements and features to the purchase section',
    'description': """
    - Adds VAT-inclusive unit pricing on purchase order lines.
    - Displays line numbering on purchase orders and printed purchase order reports.
    - Adds Amount Received, Amount to Bill, and Amount Billed fields to purchase orders and Purchase Analysis.
    - Extends Purchase Analysis with unit price, analytic account filtering, and a printable PDF report.
    - Automatically creates receipts and vendor bills on purchase order confirmation with configurable receipt validation and bill posting options.
    - apply discounts on purchase order lines (global, per-line or fixed amount)'
    - Adds a detailed Purchase Analysis view with a printable PDF report.
""",
    "version": "18.0",
    "category": "Dekad/Customizations",
    "author": "Dekad (Mohammed alhelal)",
    "license": "LGPL-3",
    "installable": True,
    "depends": ["base", "purchase", "purchase_stock", "stock"],
    "data": [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'wizard/purchase_order_discount_views.xml',
        "views/purchase_views.xml",
        "views/purchase_order_report.xml",
        "views/res_config_settings.xml",
        "report/purchase_order_report.xml",
        "report/purchase_report_views.xml",
        "report/custom_purchase_order_report.xml"

    ],

}
