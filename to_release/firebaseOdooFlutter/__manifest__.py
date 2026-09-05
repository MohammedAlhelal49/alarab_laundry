{
    'name': "firebaseOdooFlutter",
    'summary': "Firebase Cloud Messaging integration for Odoo",
    'description': """
        This module integrates Firebase Cloud Messaging (FCM) to send push notifications
        to mobile devices and web browsers.
    """,
    'author': "Youssef Omran",
    'website': "https://www.yourcompany.com",
    'category': 'Tools',
    'version': '18.0.2.0',
    'depends': ['base', 'mail', 'sale', 'purchase', 'account', 'stock', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/fcm_device_views.xml',
        'views/fcm_notification_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

