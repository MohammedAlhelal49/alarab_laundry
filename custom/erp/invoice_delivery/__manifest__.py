{
    'name': 'Invoice Delivery',
    'version': '18.0.1.0.0',
    'summary': 'Create delivery orders automatically from customer invoices',
    'category': 'Accounting/Accounting',
    'author': 'SMR',
    'license': 'LGPL-3',

    'depends': [
        'account',
        'stock',
    ],

    'data': [
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}