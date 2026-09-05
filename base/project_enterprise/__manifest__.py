# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Project Enterprise",
    'summary': """Bridge module for project and enterprise""",
    'description': """
Bridge module for project and enterprise
    """,
    'category': 'Services/Project',
    'version': '1.0',
    'depends': ['project', 'web_map', 'web_gantt'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/project_task_views.xml',
        'views/project_views.xml',
        'views/project_sharing_templates.xml',
        'views/project_sharing_views.xml',
        'views/project_portal_project_task_templates.xml',
        'data/project_data.xml',
    ],
    'demo': ['data/project_demo.xml'],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'project_enterprise/static/src/views/project_highlight_tasks.js',
            'project_enterprise/static/src/views/project_task_search_model.js',
            'project_enterprise/static/src/views/highlight_project_task_search_model.js',
            'project_enterprise/static/src/scss/**/*',
            'project_enterprise/static/src/components/**/*',
            'project_enterprise/static/src/views/project_task_calendar/**',
            'project_enterprise/static/src/views/project_task_tree/**',
            'project_enterprise/static/src/views/project_task_kanban/**',
            'project_enterprise/static/src/views/view_dialogs/**',
            'project_enterprise/static/src/xml/**',

            # Don't include dark mode files in light mode
            ('remove', 'project_enterprise/static/src/components/**/*.dark.scss'),
        ],
        'web.assets_backend_lazy': [
            'project_enterprise/static/src/views/project_task_map/**',
            'project_enterprise/static/src/views/project_task_graph/**',
            'project_enterprise/static/src/views/project_task_pivot/**',
            'project_enterprise/static/src/views/project_task_activity/**',
            'project_enterprise/static/src/views/task_gantt/**',
            'project_enterprise/static/src/views/project_gantt/**',
        ],
        "web.assets_web_dark": [
            'project_enterprise/static/src/components/**/*.dark.scss',
        ],
        'web.assets_unit_tests': [
            'project_enterprise/static/tests/*',
        ],
        'web.qunit_suite_tests': [
            'project_enterprise/static/tests/legacy/**/*',
        ],
        'web.assets_tests': [
            'project_enterprise/static/tests/tours/**/*',
        ],
    }
}
