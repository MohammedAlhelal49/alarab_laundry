# -*- coding: utf-8 -*-
{
    'name': "dekad_attachment",
    'summary': """
         Attanchment manegment Destem for partners
         """,
    'description': """
        Attanchment manegment Destem for partners
    """,
    'author': "Dekad software solutions",
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'dekad_core', 'dekad_parent',"mail"],
    # always loaded
    'data': [
        'security/ir_rule_data.xml',
        'security/ir.model.access.csv',
        'views/attachment_veiw.xml',
        'views/student_view.xml',
        'views/teacher_view.xml',
        'views/parent_view.xml',
    ],

}
