# custom_pos_receipt/__manifest__.py
{
    'name': 'alarab_laundry_implementation',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Add customer details to POS receipt',
    'depends': ['base','sale','account','point_of_sale','contacts' , 'dekad_additional_features'],
    'data': [
        'data/quotation_order.xml',
        'views/pos_invoice_menu.xml',
        "views/report_invoice.xml",
        "views/pos_order_views.xml",

    ],
    'assets': {
        'point_of_sale._assets_pos': [
            '/alarab_laundry_implementation/static/src/js/pos_receipt.js',
            '/alarab_laundry_implementation/static/src/js/partner_list_patch.js',
            '/alarab_laundry_implementation/static/src/xml/pos_receipt_template.xml',
            '/alarab_laundry_implementation/static/src/scss/receipt.css',
        ],
    },
    'installable': True,
    'application': False,
}
