# dekad_employee_attendance_location/__manifest__.py

{
    'name': 'Attendance Location',
    'version': '18.0.1.0.0',
    'summary': 'Manage employee attendance.',
    'category': 'Human Resources/Attendance',
    'author': 'DSS',
    'website': 'https://dekad.tech',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'hr',
        'mail',
        'hr_attendance',
        'web',
        'hrms_dashboard',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_attendance_views.xml',
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'dekad_employee_attendance_location/static/src/js/attendance_location.js',
            'dekad_employee_attendance_location/static/src/js/dashboard_extension.js',
            'dekad_employee_attendance_location/static/src/css/dashboard_extension.css',
        ],

    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
