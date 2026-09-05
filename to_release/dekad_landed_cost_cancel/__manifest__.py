{
    'name': 'Dekad Landed Cost Cancel & Correct',
    'version': '18.0.1.1.0',
    'category': 'Inventory/Valuation',
    'summary': 'Cancel or correct a validated Landed Cost',
    'depends': ['stock_landed_costs', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/landed_cost_views.xml',
        'wizard/correct_landed_cost_wizard_views.xml',
    ],
    'author': 'Dekad',
    'installable': True,
    'license': 'LGPL-3',
}
