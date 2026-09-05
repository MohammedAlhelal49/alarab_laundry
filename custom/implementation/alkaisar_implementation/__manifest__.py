# ALKAISAR_implementation/__manifest__.py

{
    'name': 'ALKAISAR Implementation',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'ALKAISAR Implementation',
    'author': 'Dekad',
    'depends': ['sale_management', 'product', 'mrp', 'base' , 'account' , 'account_accountant'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_line_view.xml',
        'views/sale_order_view.xml',
        'views/res_users_views.xml',
        'views/sale_customer_price_history_views.xml',
        'views/res_config_settings_view.xml',
    ],
    'installable': True,
    'application': False,
}
