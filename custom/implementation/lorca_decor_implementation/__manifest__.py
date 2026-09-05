# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017-2018 Tecnativa - Jairo Llopis
# Copyright 2018-2019 Tecnativa - Alexandre Díaz
# Copyright 2021 ITerra - Sergey Shebanin
# Copyright 2023 Onestein - Anjeel Haria
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Lorca Decor Implementation",
    "summary": "Lorca Decor Implementation",
    "version": "18.0",
    'category': 'Dekad',
    "author": "Dekad (Mohammed alhelal)",
    "license": "LGPL-3",
    "installable": True,
    "depends": ["base", "web", "account"],
    "data": [
        "views/account_report.xml",
    ],

    "assets": {
        'web.report_assets_common': [
            "lorca_decor_implementation/static/src/scss/layout_background.scss",
        ],

        'web.report_assets_pdf': [
            "lorca_decor_implementation/static/src/scss/additional.css",
        ],

    },

}
