
{
    'name': 'Barada Implementation',
    'version': '18.0.1.0.1',
    'summary': 'Barada Implementation',
    'description': """
     - Extends the existing Dekad Analytic Dashboard.
     - CRM reservation management with booking dashboard and status filters
    """,
    'depends': [
        'base','hr','account','analytic','dekad_analytic_report','crm'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/crm_reservation_sequence.xml',
        'data/reservation_delay_reason_data.xml',
        'data/hr_employee_group_data.xml',

        'views/hr_employee_views.xml',
        'views/dashboard_inherit.xml',
        'views/crm_lead_view.xml',
        'views/crm_reservation_views.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'barada_implementation/static/src/reservation_dashboard/reservation_dashboard.js',
            'barada_implementation/static/src/reservation_dashboard/reservation_dashboard.xml',
            'barada_implementation/static/src/reservation_dashboard/reservation_dashboard.scss',
        ],
    },
    'installable': True,
    'application': False,
}
