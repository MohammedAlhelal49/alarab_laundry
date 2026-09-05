# -*- coding: utf-8 -*-
###############################################################################
#
#    Dekad Inc
#    Copyright (C) 2009-TODAY Dekad Inc(<http://www.Dekad.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

{
    'name': 'Web Dekad',
    'category': 'Website',
    "sequence": 3,
    'version': '18.0.1.0',
    'license': 'LGPL-3',
    'author': 'Dekad Inc',
    'website': 'http://www.dekad.org',
    'data': [
        'views/base.xml',
        'views/buttons_template.xml',
        'views/student_pages_buttons.xml',
        # 'views/homepage.xml',
        # 'views/translate_template.xml',
        'website/main.xml'
    ],
    'depends': [
        'website','portal','web'
    ],
    'application': True,
    'assets': {
        'web.assets_frontend': [
                # '/dekad_web/static/src/lib/jquery-ui.min.js',
                # '/dekad_web/static/src/js/twitter-bootstrap.js',
                ('include', 'web._assets_bootstrap_frontend'),
                '/dekad_web/static/src/js/toaster.js',
                '/dekad_web/static/src/js/main.js',
                # '/dekad_web/static/src/js/file_handler.js',
                '/dekad_web/static/src/scss/main.scss',
                '/dekad_web/static/src/scss/portal.scss',
                '/dekad_web/static/src/scss/public.scss',
                '/dekad_web/static/src/css/toaster.css',

            # '/dekad_web/static/src/css/portal_home.css',
            # '/dekad_web/static/src/css/student_school_info.css',
            # '/dekad_web/static/src/css/student_profile.css',
            # '/dekad_web/static/src/css/parent_student.css',
            # '/dekad_web/static/src/css/student_achievement.css',
            # '/dekad_web/static/src/js/change_file_btn.js',
        ],
    }
}
