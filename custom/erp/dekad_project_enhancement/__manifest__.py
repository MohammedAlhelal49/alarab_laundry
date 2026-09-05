{
    'name': 'Dekad Project Enhancement',
    'version': '18.0.1.0.0',
    'category': 'Project',
    'summary': 'Lets Project Managers view all To-do tasks, regardless of assignment.',
    'license': 'LGPL-3',
    'depends': ['project', 'project_todo'],
    'description': """

    - Allowing Project Managers to view all To-dos, regardless of assignment.
    - Granting Project Managers full access and visibility to all project tasks.
""",
    'data': [
        'security/todo_access_rules.xml',
        "views/project_task_manager_views.xml",
    ],
    'installable': True,
    'application': False,
}
