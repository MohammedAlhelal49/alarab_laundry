# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017-2018 Tecnativa - Jairo Llopis
# Copyright 2018-2019 Tecnativa - Alexandre Díaz
# Copyright 2021 ITerra - Sergey Shebanin
# Copyright 2023 Onestein - Anjeel Haria
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Dekad payment warning",
    "summary": "Add Payment warning  customized message from the company informations , this could be configured only from the dekad super user ",
    "version": "18.0",
    "category": "Customizations",
    "author": "Dekad (Mohammed alhelal)",
    'license': 'LGPL-3',
    'data': [
        "views/res_config_settings.xml"
    ],
    'depends': ['base', 'base_setup'],
    "assets": {
        "web.assets_backend": [

            'dekad_payment_warning/static/src/js/webclient_banner.js',
            'dekad_payment_warning/static/src/xml/banner_template.xml',

        ]
    },
'images': [
    'static/description/icon.png',
],

}
