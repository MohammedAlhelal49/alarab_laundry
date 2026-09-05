{
    "name": "Dekad additional features",
    "summary": "Add some technical features to odoo core system and product section",
    'description': """
    *** Add Additional Features to the system ***
-- Select and uninstall Apps from the apps list

-- Show English numerals in date fields for Arabic interface

-- Force creation of all missing product variants for dynamic-attribute products

-- Configurable display of attribute names and values in the product variant name.
  
-- Generate variations pricelist rules from the selected products

-- Prevent data update when select multi company 

-- Enhance the search of the products in all the system sections

-- Add the related user for each contact record if exist => this will be important for contacts users filters

-- Send Dynamic WhatsApp messages to contacts

-- Improve Contact list management by allowing authorized Sales users to edit the Company field directly from the list view.

-- adds a clone/duplicate button to the order/invoice lines for:Sale Orders, Purchase Orders, Invoices / Account Moves
        
-- Company Attachment Notification.

-- Configure required fields, duplicate prevention, and duplicate warnings per model/field.

-- Automatically assign the current company to newly created Contacts and Product Templates.

-- Prevent editing Attributes & Variants if DONE stock moves exist or posted accounting moves exist

- Search products in English, Arabic, barcode and internal reference
""",
    'author': 'Dekad software solutions',
    "version": "18.0",
    "category": "Dekad/Customizations",
    "license": "LGPL-3",
    "installable": True,
    "depends": ["base","base_setup","web", "mail", "product" , "contacts",'sale_management', 'purchase', 'account','stock'],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/contacts_whatsapp_template.xml",
        "data/mail_template.xml",
        "data/ir_cron.xml",
        "views/ir_module_views.xml",
        'views/product_template_views.xml',
        "views/res_partner_views.xml",
        "views/send_whatsapp_wizard_views.xml",
        "views/whatsapp_template_views.xml",
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
        "views/res_config_settings.xml",
        "views/company_attachment_views.xml",
        "views/res_company_views.xml",
        "views/required_field_views.xml",
        "views/product_search_views.xml",
        "views/base_document_layout_views.xml",
        "views/report_layout.xml",

        "views/menus.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'dekad_additional_features/static/src/xml/duplicate_line.xml',
            'dekad_additional_features/static/src/js/duplicate_line.js',
            'dekad_additional_features/static/src/js/purchase_order_line_duplicate.js',
            'dekad_additional_features/static/src/js/account_move_duplicate_line.js',
            "dekad_additional_features/static/src/js/list_confirmation_dialog_patch.js",

            # 'dekad_additional_features/static/src/**/*',
        ],
    },
}
