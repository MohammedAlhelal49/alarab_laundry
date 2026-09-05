{
    'name': 'Dekad Activity Logger',
    'version': '18.0.1.0.0',
    'category': 'Administration/Tools',
    'summary': 'Track and log system operations (Create, Update, Delete) across configured sections.',
    'description': """
Dekad Activity Logger
=====================
This module provides a centralized, performance-optimized activity logger to track system changes. 

Key Features:
-------------
* **Model Configuration:** Choose exactly which models (sections) to track via the UI.
* **Granular Tracking:** Records Create, Update, and Delete operations.
* **Detailed History:** Captures the exact 'before' and 'after' state of fields in a clean, visual format.
* **Secure:** Non-admin users can generate logs but cannot delete them.
    """,
    'author': 'Dekad (Mofeed Dozkanji)',
    'depends': ['base'],
    'data': [
        'security/activity_logger_groups.xml',
        'security/ir.model.access.csv',
        'security/activity_logger_security.xml',

        'wizard/activity_logger_filter_wizard_views.xml',
        'wizard/activity_logger_kpi_wizard_views.xml',

        'views/activity_logger_kpi_views.xml',
        'views/activity_logger_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
