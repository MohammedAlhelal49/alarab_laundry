# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017-2018 Tecnativa - Jairo Llopis
# Copyright 2018-2019 Tecnativa - Alexandre Díaz
# Copyright 2021 ITerra - Sergey Shebanin
# Copyright 2023 Onestein - Anjeel Haria
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    "name": "Dekad Account UAE vat format",
    "summary": "Add the UAE vat designing formating to the Pinted pdf invoice",
    "version": "18.0",
    "category": "Dekad/Customizations",
    "author": "Dekad (Mohammed alhelal)",
    "license": "LGPL-3",
    "installable": True,
    "depends": ["account" , "base" , "l10n_ae" ],
    "data": [
        "views/report_invoice.xml",
    ],

    "assets": {
        # "web.assets_backend": [
        #     "/dekad_account_uae_vat_format/static/src/scss/backend.scss",
        # ],
    },
}
