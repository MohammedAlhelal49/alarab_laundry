# -*- coding: utf-8 -*-

{
    'name': 'Dekad Weekly Planner',
    'version': '18.0.1.0.0',
    'category': 'Education',
    'summary': 'Teacher Weekly Planning and Schedule Management',
    'description': """
        Teacher Weekly Planner Module
        ==============================

        Features:
        ---------
        * Weekly schedule planning for teachers
        * Daily time slot management
        * Subject and classroom assignment
        * Activity type categorization
        * Calendar and timeline visualization
        * PDF weekly timetable reports
        * Validation for overlapping schedules
        * Auto-generation of weekly templates
        * Teacher self-service portal

        This module allows teachers to plan their weekly activities including:
        - Lessons
        - Preparation time
        - Meetings
        - Other activities
    """,
    'author': 'Dekad',
    'website': 'https://www.dekad.tech',
    'depends': [
        'base',
        'mail',
        'dekad_core',
        'dekad_classroom',
        'dekad_timetable',
    ],
    'data': [
        # Security
        'security/weekly_planner_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/ir_sequence_data.xml',

        # Views
        'views/teacher_weekly_planner_views.xml',
        'views/teacher_weekly_planner_line_views.xml',
        'views/menu_items.xml',

        # Reports
        'report/weekly_planner_report.xml',
        'report/weekly_planner_template.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
