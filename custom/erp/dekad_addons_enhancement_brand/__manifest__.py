# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017-2018 Tecnativa - Jairo Llopis
# Copyright 2018-2019 Tecnativa - Alexandre Díaz
# Copyright 2021 ITerra - Sergey Shebanin
# Copyright 2023 Onestein - Anjeel Haria
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Dekad Community branding enhancement",
    "summary": "Deactivate some odoo crons jops and handle some templates (reset password) designing",
    "version": "18.0",
    "category": "Customizations",
    "author": "Dekad (Mohammed alhelal)",
    "license": "LGPL-3",
    "depends": ["base", "digest", "web", "base_setup", "auth_signup" , "mail_bot" , "mail"],
    "data": [
        "data/config_data.xml",
        "views/base_document_layout_views.xml",
        "views/mail_views.xml",
        "views/web_views.xml",

    ],
    "assets": {
        "web.assets_frontend": [
            "/dekad_addons_enhancement_brand/static/src/scss/portal.scss",
            "/dekad_addons_enhancement_brand/static/src/js/portal.js",
        ],

        "web.assets_backend": [
            "/dekad_addons_enhancement_brand/static/src/webclient/user_menu/user_menu.xml",
            "/dekad_addons_enhancement_brand/static/src/js/web_window_title.js",
            "/dekad_addons_enhancement_brand/static/src/scss/backend.scss",
        ],
    },
}
