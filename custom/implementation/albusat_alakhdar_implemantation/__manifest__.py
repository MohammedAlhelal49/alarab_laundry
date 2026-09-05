{
    'name': 'Al Busat Al Akhdar - Implementation',
    'version': '18.0.1.0.0',
    'summary': 'Custom implementation for Al Busat Al Akhdar Agricultural Services Co.',
    'category': 'Inventory',
    'depends': ['stock', 'product'],
    'data': [
        'views/product_views.xml',
        'report/delivery_note_report.xml',
    ],
    'installable': True,
    'application': False,
}
