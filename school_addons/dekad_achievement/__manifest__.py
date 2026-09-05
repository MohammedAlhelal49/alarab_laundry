# -*- coding: utf-8 -*-
{
    'name': "Dekad achievement",
    'summary': """Awards""",
    'description': """
        Awards
    """,
    'author': "Dakad Software Solutions",
    'license': 'LGPL-3',
    'category': 'Education',
    'sequence': 7,
    'version': '18.0',
    'depends': ['dekad_core', 'base', 'mail'],
    'data': [
        'security/ir_rule_data.xml',
        'security/ir.model.access.csv',
        'views/achievement_type_view.xml',
        'views/student_achievement_view.xml',
        'views/student_achievement_assign_view.xml',
        'views/student_view.xml',
        'views/teacher_achievement_view.xml',
        'views/teacher_achievement_assign_view.xml',
        'views/teacher_view.xml',
        'wizard/multi_student_achievement_wizard.xml',
        'wizard/multi_teacher_achievement_wizard.xml',
        'menus/menu.xml',
        # website,
        'website/main.xml',
        # demo',
        # 'demo/de_achievement.xml',
    ],
}
