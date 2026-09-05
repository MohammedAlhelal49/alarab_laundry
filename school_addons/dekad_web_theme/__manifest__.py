{
    'name': 'Dekad School Theme',
    'summary': 'Private School Theme',
    # 'category': 'Theme',
    'version': '18.0.1.0',
    'author': 'dekad',
    'depends': [
        'website',
        'theme_default',
    ],
    'data': [
        'views/homepage.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            '/dekad_web_theme/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            '/dekad_web_theme/static/src/scss/style.scss',
            '/dekad_web_theme/static/src/js/home.js',
        ],
    },
    'images': [
        'static/description/icon.png',
    ],
    'license': 'LGPL-3',
    'application': True,
    'installable': True,
}
