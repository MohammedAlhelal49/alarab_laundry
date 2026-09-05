{
    'name': 'Dekad Website Floating Contact Buttons',
    'version': '18.0.1.0.0',
    'summary': 'Adds WhatsApp and Phone buttons to website footer',
    'category': 'Website',
    'author': 'Dekad',
    'depends': ['website'],
    'data': [
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'dekad_website_floating_contact_buttons/static/src/css/contact_buttons.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
