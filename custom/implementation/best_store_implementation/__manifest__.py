{
    "name": "best store implementation",
    "version": "18.0.0.1",
    'author': 'Dekad',
    "depends": ["base", "account", 'sale', 'hr', 'mail', 'purchase', 'product', 'point_of_sale', 'web', 'stock',
                'dekad_pos_sale_enhancement', 'dekad_purchase_enhancement','pos_hr'],
    "description": """    
        -- Calculate and display Invoice Total Cost, Profit, and Profit Margin, including line-level Cost and Profit.
    
        -- Restrict visibility of Cost and Profit information using dedicated security groups.
    
        -- Display Product Images, Barcodes, and custom Links on Sales and Purchase Order lines.
    
        -- Enhance Sales and Purchase Order PDF reports with Product Images and Barcodes, including Line Numbers on Sales Orders.
        
        -- Improve editable list navigation by moving vertically between rows using the Enter key in Sales and Purchase Orders.
    
        -- Automatically switch the POS numpad to Price mode when selecting or adding products.
    
        -- Display Employee PIN as a password field to improve privacy.
    
    """,
    "data": [
        'security/groups.xml',
        'report/report_saleorder_image.xml',
        'report/purchase_order_report_image.xml',
        'views/sale_oder_line_view.xml',
        'views/purchase_order_line_view.xml',
        'views/account_move_cost_profit_views.xml',
        'views/hr_employee_views.xml',
        'views/stock_picking_view.xml',

        

    ],
    'assets': {
        'web.assets_backend': [
            'best_store_implementation/static/src/js/list_vertical_navigation.js',
        ],
        'point_of_sale._assets_pos': [
            'best_store_implementation/static/src/js/pos_price_focus.js',
        ],
    },

    "application": False,
    "installable": True,
}
