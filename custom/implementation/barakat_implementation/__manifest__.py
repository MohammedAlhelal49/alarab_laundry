# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017-2018 Tecnativa - Jairo Llopis
# Copyright 2018-2019 Tecnativa - Alexandre Díaz
# Copyright 2021 ITerra - Sergey Shebanin
# Copyright 2023 Onestein - Anjeel Haria
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Barakat implementation",
    'summary': 'Add some enhancements and features to barakat project',
    'description': """
    -- add the a configurable feature to ad a default vendor to the new created request for qoutation
    -- prevent the purchase user from confirm the request for qoutation
    -- if the request for qoutation created from purchase user => send activity to all purchase managers to confirm the document
      """,
    "version": "18.0",
    "category": "Dekad/Customizations",
    "author": "Dekad (Mohammed alhelal)",
    "license": "LGPL-3",
    "installable": True,
    "depends": ["base", "purchase", "purchase_stock"],
    "data": [
        'security/ir.model.access.csv',
        "security/ir_rule_data.xml",
        "views/purchase_views.xml",
        "views/res_config_settings.xml",
    ],

}
