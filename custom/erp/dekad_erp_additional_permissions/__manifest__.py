{
    'name': 'dekad erp additional permissions',
    'version': '1.0',
    'summary': 'Restricts key actions (Validate, Cancel, Delete, Return) in Sales ,Contacts ,Purchase , Accounting and Inventory modules based on user groups.',
    'description': '''
This module enhances security and control over key operational actions in Odoo:
- Restrict create and delete operations for Contacts, Products, and Chart of Accounts.
- Restrict confirmation, cancellation, deletion, posting, and reset to draft for Sales, Purchases, Payments, and Journal Entries.
- Restrict validation, cancellation, deletion, and return operations for Inventory transfers.
- Restrict who can change a Contact's Name, Email, Phone or Mobile.
''',
    'category': 'Tools',
    'depends': ['sale_management', 'purchase', 'account', 'stock',"contacts"],
    'data': [
        'security/sale_security.xml',
        'security/inventory_security.xml',
        'security/purchase_security.xml',
        'security/accounting_security.xml',
        'security/product_security.xml',
        'security/contact_permission_groups.xml',

    ],
    'installable': True,
    'application': False,
    'post_init_hook': 'assign_default_permission_groups',
}
