# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017-2018 Tecnativa - Jairo Llopis
# Copyright 2018-2019 Tecnativa - Alexandre Díaz
# Copyright 2021 ITerra - Sergey Shebanin
# Copyright 2023 Onestein - Anjeel Haria
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Aflaj alain Implementation",
    "summary": "Aflaj alain Implementation",
    "version": "18.0",
    'category': 'Dekad',
    "author": "Dekad (Mohammed alhelal)",
    "license": "LGPL-3",
    "installable": True,
    "depends": ["base", "web", "account", "stock", "stock_account" , "dekad_additional_features" , "dekad_stock_location_additional_cost" , "point_of_sale" ],

    "data": [
        "data/ir_sequence_data.xml",
        "security/ir.model.access.csv",
        "views/care_period_input_views.xml",
        "views/production_period_input_views.xml",
        "views/farm_type.xml",
        "views/stock_picking.xml",
        "views/res_config_settings.xml",
    ],

    "assets": {
        'point_of_sale._assets_pos': [
            'aflaj_alain_implementation/static/src/**/*'
        ],
        'web.report_assets_common': [
            "aflaj_alain_implementation/static/src/scss/layout_background.scss",
        ],
        'web.report_assets_pdf': [
            "aflaj_alain_implementation/static/src/scss/additional.css",
        ],

    },

}
