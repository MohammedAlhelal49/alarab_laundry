{
    'name': 'Product Transfer (ID-based)',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Transfer all moves from one product to another by updating product_id across all related tables',
    'author': 'Dekad',
    'depends': ['stock', 'account', 'purchase', 'sale_management', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_transfer_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
