# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017-2018 Tecnativa - Jairo Llopis
# Copyright 2018-2019 Tecnativa - Alexandre Díaz
# Copyright 2021 ITerra - Sergey Shebanin
# Copyright 2023 Onestein - Anjeel Haria
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Dekad Pos sale enhancement",
    "summary": "Dekad Pos sale enhancement",
    "version": "18.0",
    "author": "Dekad (Mohammed alhelal)",
    "license": "LGPL-3",
    "installable": True,
    "depends": ["web", "base", "point_of_sale", "pos_sale", "pos_set_default_customer",
                "prt_report_attachment_preview", "pos_discount", "hr", 'stock', 'account', "stock_account",
                'dekad_stock_enhancement', 'sale', "portal", "dekad_additional_features",'dekad_account_enhancement'],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/quotation_order.xml",
        'data/mail_template.xml',
        "views/pos_config_view.xml",
        'views/product_view.xml',
        "views/res_users_view.xml",
        'views/pos_order_views.xml',
        'views/pos_invoice_menu.xml',
        "views/pos_customer_payments_menu.xml",
        'views/report_invoice_bilingual.xml',
        "views/account_move_views.xml",
        "views/whatsapp_template_views.xml",

    ],

    'assets': {
        'point_of_sale._assets_pos': [
            'dekad_pos_sale_enhancement/static/src/**/*',
        ],
    },
    "description": """
    - Auto-download invoice PDFs and force invoice creation on order validation.
    - Restrict POS cashiers to selected HR employees.
    - Limit global and per-line discounts.
    - Enforce minimum and maximum product selling prices.
    - Prevent selling outside configured price limits unless price override is allowed.
    - Restrict POS manual price modifications to selected employees through configurable employee permissions.
    - Configure an Additional Charge button with configurable product, percentage, and automatic tax calculation.
    - Enhance the POS product search with fuzzy matching, bilingual (Arabic/English) support, barcode, and internal reference search.
    - Support bilingual (Arabic/English) product names for POS search, display, receipts, and invoice reports.
    - Display customer names on POS receipts.
    - Display the "Tax Invoice" heading on POS receipts for UAE companies.
    - Display minimum and maximum product prices in the POS Product Information popup.
    - Configure multiple UoMs per product or template with automatic synchronization to variants, ensuring each configuration is unique and includes the reference UoM. Users can select alternate UoMs directly from the POS with automatic quantity conversion and clear UoM display on order lines.
    - Allow cancellation of validated POS orders.
    - Allow correction of validated POS orders by creating a corrected draft order.
    - Add Invoices and Customer Payments menus under the Point of Sale application.
    - Add the partner contact (phone/mobile) field to Customer Invoices with search and group-by support.
    - Restrict the "Validate" button on Customer Payments to Accounting users.
    - Hide the Cash Control section in the POS session closing popup.
    - Add a "POS Cash Control Bypass" security group allowing authorized users to access Cash Control even when hidden.
    - Display bilingual (Arabic/English) product names on customer invoices when Arabic is installed.
    - Send invoices via WhatsApp from both POS and Accounting using configurable templates.
    - Add a WhatsApp button on Customer Invoices for quick invoice sharing.
    - Support configurable WhatsApp templates per POS with invoice number, amount, and portal link placeholders.
    - Display product variant names in POS order lines and reports.
    - Send email and activity notifications when a POS session is closed with a configurable cash difference threshold.
    - Allow selecting employees to receive POS cash difference notifications.
    - Enhance the discount popup by displaying both percentage and calculated amount.
    - Restrict or warn cashier when product QTY is zero or negative
    - Uses the configured refund income account for POS return and refund invoice lines.
""",

}
