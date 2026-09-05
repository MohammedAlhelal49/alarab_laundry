# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017-2018 Tecnativa - Jairo Llopis
# Copyright 2018-2019 Tecnativa - Alexandre Díaz
# Copyright 2021 ITerra - Sergey Shebanin
# Copyright 2023 Onestein - Anjeel Haria
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Dekad super user",
    "summary": "Add a super user (dekad) and make only this user can access the settings and the apps menu ,  add users limit feature",
    "version": "18.0",
    "category": "Customizations",
    "author": "Dekad (Mohammed alhelal)",
    'license': 'LGPL-3',
    'data': [
"views/res_company.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings.xml",
    ],
    'depends': ['base', 'base_setup', 'contacts'],
    "assets": {
        "web.assets_backend": [
            "/dekad_super_user/static/src/scss/backend.scss",
        ],
    },

}
