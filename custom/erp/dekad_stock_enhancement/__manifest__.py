# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017-2018 Tecnativa - Jairo Llopis
# Copyright 2018-2019 Tecnativa - Alexandre Díaz
# Copyright 2021 ITerra - Sergey Shebanin
# Copyright 2023 Onestein - Anjeel Haria
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    "name": "Dekad stock enhancement",
    "version": "18.0.1.0",
    "summary": "Add some additional features and enhancement to the inventory App",
    "description": """
    - Cancel validated inventory transfers and restore them to Draft state using a dedicated cancellation wizard.

    - Safely unreserve stock, back up and restore quantities, and preserve inventory consistency during transfer cancellation.

    - Automatically identify cancellation-generated stock valuation layers and remove their related reversal journal entries when appropriate.

    - Generate Product Stock PDF reports displaying on-hand quantity, unit cost, and total inventory value.

    - Synchronize inventory transfers between companies without requiring Sales Orders or Purchase Orders by automatically generating draft receipts and deliveries in the corresponding company.

    - Configure automatic inter-company inventory receipts and deliveries independently for each company.

    - Prevent recursive inter-company transfer generation while maintaining traceability through linked chatter messages.

    - Preserve the scheduled transfer date as the completion date when validating inventory transfers.

    - Add analytic account support to stock moves and stock move lines with automatic distribution to inventory valuation journal entries.

    - Display and automatically compute Unit Cost and Cost Amount on stock moves and stock move lines.

    - Add manual sequencing, line numbering, and drag-and-drop reordering for stock move lines.

    - Extend stock move and stock move line search views with analytic account filters and group-by options.

    - Enhance inventory transfer views with analytic accounting and cost analysis information.

    - Add filters to distinguish regular inventory valuations from cancellation reversal valuations.

    - Provide server actions to update analytic distributions and clean up cancellation-related journal entries.
    
    - Make signature requirement for Delivery Orders and Internal Transfers configurable from Inventory Settings.
    
    - Manage and update product costs directly from Physical Inventory with automatic stock valuation
    
    - Restrict Apply / Apply All buttons on Physical Inventory to a dedicated access group
""",
    "author": "Dekad (Mohammed Khair)",
    "category": "Customizations",
    'license': 'LGPL-3',
    "depends": ["stock", "stock_account",'product'],
    "data": [
        "security/ir.model.access.csv",
        'security/security.xml',

        "views/res_config_settings_views.xml",
        "report/product_stock_report_template.xml",
        "report/product_stock_report_action.xml",
        "views/stock_picking_view.xml",
        "views/stock_valuation_layer_views.xml",
        "views/wizard_views.xml",
        'views/stock_quant_views.xml',
        'views/product_template_views.xml',
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
