# attendance_location/__manifest__.py

{
    'name': 'HR Attendance Location Integration',
    'version': '18.0.1.0.0',
    'summary': 'Manage employee attendance linked to patients with GPS tracking.',
    'description': """
This module integrates patient management with employee attendance,
allowing GPS-based location tracking during check-in/check-out processes.

Key Features:
- Link employees to multiple patients.
- Track GPS coordinates during check-in and check-out.
- GeoIP-based localization support.
- Patient assignment dashboard integration.
- Manual and automatic patient selection.
""",
    'category': 'Human Resources/Attendance',
    'author': 'Dekad Tech (Mohammed Khair)',
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
        'views/patient_views.xml',
        'views/res_partner_views.xml',
        'views/medical_note_history_views.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'attendance_location/static/src/js/attendance_location.js',
            'attendance_location/static/src/js/dashboard_extension.js',
            'attendance_location/static/src/js/checkedin_card.js',
            'attendance_location/static/src/js/hr_dashboard_patch.js',
            'attendance_location/static/src/css/dashboard_extension.css',
            'attendance_location/static/src/css/patient_selection.css',
            'attendance_location/static/src/css/patient_modal.css',
        ],

    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
