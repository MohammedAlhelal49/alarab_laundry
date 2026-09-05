{
    'name': 'London Laundry POS Receipt',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Custom POS receipt for laundry businesses',
    'author': 'Dekad',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'london_laundry_implementation/static/src/css/receipt.css',
            'london_laundry_implementation/static/src/js/order_receipt_patch.js',
            'london_laundry_implementation/static/src/xml/receipt.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
