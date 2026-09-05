{
    'name': 'Al Omran Theme',
    'version': '18.0.2.0.0',
    'category': 'Website',
    'summary': 'Complete website theme for Al Omran Training Center',
    'description': """
        Al Omran Training Center Website Theme
        =======================================
        - Dynamic Pop-up Offers with CRM Integration
        - Branch Locations
        - Floating Call Button
        - Bilingual Support (Arabic/English)
        - Full RTL Support for Arabic
    """,
    'author': 'Dekad',
    'depends': [
        'website',
        'mail',
        'crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/templates.xml',
        'views/rtl_template.xml',
        'views/redirects.xml',
        'views/pages/teachers.xml',
        'views/pages/languages.xml',
        'views/pages/it_programs.xml',
        'views/navbar.xml',
        'views/floating_call.xml',
        'views/popup_offer_views.xml',
        'views/crm_lead_views.xml',
        'views/popup_offer.xml',
        'views/pages/home.xml',
        'views/pages/about.xml',
        'views/pages/courses.xml',
        'views/pages/branches.xml',
        'views/pages/branch_detail.xml',
        'views/pages/contact.xml',
        'views/disable_default_webiste_menu.xml',
        'data/popup_offer_demo.xml',

    ],
    'assets': {
        'web.assets_frontend': [
            'alomran_theme/static/src/scss/navbar.scss',
            'alomran_theme/static/src/scss/home.scss',
            'alomran_theme/static/src/css/about_style.css',
            'alomran_theme/static/src/css/branches.css',
            'alomran_theme/static/src/css/ltr.css',
            'alomran_theme/static/src/css/rtl.css',
            'alomran_theme/static/src/js/main.js',
            'alomran_theme/static/src/js/popup_offer.js',
            'alomran_theme/static/src/js/course-registration.js',
            'alomran_theme/static/src/js/courses-page.js',
            'alomran_theme/static/src/js/rtl_handler.js',

        ],
    },
'images': [
        'static/src/img/logo.png',
        'static/src/img/hero-bg.jpg',
        'static/src/img/branches/sharjah.jpg',
        # 'static/src/img/logo.svg',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}