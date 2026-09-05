{
    'name': 'Manufacturing additional features and enhancements',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': 'Validate BoM before confirming Sale Order',
    'description': """
    - Create empty Manufacturing bill of material for the saled product
    - Make the sale - manufacturing product in one click  
    - Actual Start Date on contracts
""",
    'author': 'Dekad LLC',
    'depends': ['sale', 'mrp', 'stock'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
