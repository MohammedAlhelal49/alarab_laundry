{
    'name': 'Mobile App Portal',
    'version': '18.0.1.1.0',
    'summary': 'Manage mobile sub-app configurations and dynamic access permissions.',
    'description': """
        This module allows Odoo administrators to manage mobile applications/features 
        (Barcode, Attendance, Expenses, etc.) and dynamically control which users 
        and employees have access to which mobile apps.
    """,
    'category': 'Tools',
    'author': 'Youssef Omran',
    'license': 'LGPL-3',
    'depends': ['base', 'hr'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/mobile_app_data.xml',
        'views/mobile_app_config_views.xml',
        'views/res_users_views.xml',
        'views/hr_employee_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
}
