{
    'name': 'Photon implemnatation',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Custom striped report header and footer',
    'author': 'DSS',
    'license': 'LGPL-3',
    'depends': ['web','sh_pdc'],
    'data': [
        'views/report_layout.xml',
        'views/pdc_wizard_template.xml',
        'views/report_invoice.xml',
        'views/payment_receipt.xml',
    ],
    'installable': True,
    'application': False,
}