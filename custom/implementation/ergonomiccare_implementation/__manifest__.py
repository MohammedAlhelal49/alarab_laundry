{
    'name': 'Ergonomic Care Implementation',
    'description': '''
    - Adds a dedicated Patient Information tab in CRM Opportunities to manage patient and healthcare-related information.
    - Allows employees to select a patient and manage medical details such as MR No., Theqa No., related products, and product description.
    - Automatically loads patient information from the contact if it already exists; otherwise, entered data is saved back to the patient record.
    - Enables creating quotations and sales orders linked to patients, automatically transferring patient data from CRM.
    - Extends Customer Invoices with patient, claim, LPO, and authorization information.
    - Adds manufacturer, warranty, and delivery duration to Sales Orders and displays them clearly in PDF reports.
    - Ensures patient information is carried forward from confirmed Sales Orders to Stock Pickings.
    - Extends Stock Pickings with patient-related fields and customizes Delivery Slip PDFs to display patient, manufacturer, warranty, delivery duration, and authorization details.
    - Requires attachments and a signed delivery slip before validating Delivery Orders.
    - Validates Medical Report and Measurement attachments to accept PDF files only.
    - Prevents moving opportunities to locked CRM stages, with configurable user permissions to bypass the restriction.
    - Adds duplicate detection for contacts (Name, Phone, Mobile, and MR No.) with configurable policies to either display a warning or prevent duplicates.
    - Adds duplicate detection for products (Name) with configurable policies to either display a warning or prevent duplicates.
''',
    'version': '18.0',
    'summary': 'Ergonomic Care Implementation',
    'depends': ['sale', 'crm', 'product', 'stock','sale_crm','base','account','web'],
    'data': [
        "security/ir.model.access.csv",

        'views/sale_order_view.xml',
        'views/crm_lead_view.xml',
        'views/res_partner_view.xml',
        'views/sale_order_report.xml',
        'views/stock_picking_view.xml',
        'views/report_deliveryslip.xml',
        'views/report_invoice_custom.xml',
        "views/res_users_views.xml",
        "views/res_config_settings.xml",
        "views/product_template.xml",

    ],
    'assets': {
        'web.assets_web': [
            'ergonomiccare_implementation/static/src/css/sign_hide_auto.scss',

        ],
    },

    'installable': True,
    'application': False,
}
