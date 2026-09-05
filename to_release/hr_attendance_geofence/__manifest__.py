# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'HR Attendance Geofence',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Geofence-based attendance check-in/check-out validation',
    'description': """
HR Attendance Geofence
======================
Adds geofencing capabilities to the HR Attendance module.

Features:
- Define geofence zones (circular areas) on a map with center coordinates and radius
- Assign multiple geofence zones to employees
- Server-side validation: employees can only check-in/check-out when inside their assigned geofence
- JSON-RPC API endpoints for mobile app integration
- Company-level toggle to enable/disable geofence enforcement
- Per-employee bypass option for remote workers
    """,
    'author': 'Custom',
    'website': '',
    'depends': ['hr_attendance'],
    'data': [
        'security/hr_attendance_geofence_security.xml',
        'security/ir.model.access.csv',
        'views/geofence_zone_views.xml',
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
