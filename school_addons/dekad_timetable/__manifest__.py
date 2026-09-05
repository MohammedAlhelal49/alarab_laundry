{
    'name': "Dekad Timetable",
    'summary': "Manage and generate school timetables manually or automatically",
    'description': """
        This module allows school administrators to create and manage classroom timetables.
        Timetables can be generated automatically based on constraints or manually created by users.
    """,
    'author': "Dekad Software Solutions",
    'website': "https://www.dekad.com",
    'category': 'Education',
    'version': '18.0',
    'depends': ['base', 'dekad_core', 'dekad_classroom'],
    'data': [
        'security/ir.model.access.csv',

        'views/timetable_views.xml',


        'views/report.xml',  # contains action_report_timetable

        'views/subject_views.xml',

        'views/timetable_report.xml',
        'views/generate_timetable_wizard_view.xml',
        'views/timetable_line_views.xml',
        'views/timetable_grid_template.xml',
        'views/session_slot_views.xml',
        'views/period_views.xml',
        'views/wizard_views.xml',
        # 'views/timetable_matrix_template.xml',
        'views/menu.xml',
        # website
        'web/main.xml',

    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
