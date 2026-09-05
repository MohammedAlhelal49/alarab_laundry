{
    "name": "Real Estate",
    "version": "18.0.1.0.0",
    "category": "Real Estate",
    "author": "SMR",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "sale",
        "analytic","sale_subscription","alqatara_implementation"
    ],
    "data": [
        "security/ir.model.access.csv",

        'data/analytic_plan_data.xml',

        "views/building_views.xml",
        "views/meters_view.xml",
        "views/property_views.xml",
        "views/availability_views.xml",
        "views/rental_contract_views.xml",
        "views/sale_order_line_views.xml",

        "views/menu.xml",

    ],
    "installable": True,
    "application": True,
}