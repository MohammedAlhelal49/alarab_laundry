# -*- coding: utf-8 -*-
{
    'name': 'Dekad Partner Salesperson Scope',
    'version': '18.0.2.0.0',
    'summary': 'Restrict selected users to see only partners assigned to them, '
               'using a dedicated independent security group.',
    'description': """
    Dekad Partner Salesperson Scope
    ================================
     
    This module restricts users who are members of a dedicated security
    group ("Partner: Own Contacts Only") so they can only see partners
    where they are the assigned salesperson, plus their own partner record.
     
    Why a dedicated group?
    ----------------------
    Odoo's standard Sales groups (Salesperson, Sales Manager, Sales
    Administrator) are chained via group inheritance. An administrator
    automatically belongs to the lowest-level Salesperson group, so binding
    a restriction rule to that built-in group would also restrict admins.
     
    By defining an independent group that is NOT in the Sales inheritance
    chain, we get full control over who gets restricted: only users that
    are explicitly added to this group.
     
    What this module adds
    ---------------------
    1. A new security group: "Partner: Own Contacts Only".
    2. A record rule on res.partner scoped to this group.
    3. A record rule on res.users scoped to this group (required for
       login, session, and profile view).
    4. Two server actions available from the Users list/form view:
          * "Restrict to Own Contacts Only"    - bulk add to the group.
          * "Unrestrict (Remove Own Contacts)" - bulk remove from the group.
     
    Usage
    -----
    After installing the module:
      1. Go to Settings > Users & Companies > Users
      2. Select one or more users (list view) or open a single user
      3. Click Actions then "Restrict to Own Contacts Only"
    Administrators should NOT be added to this group.
    """,
    'category': 'Sales/CRM',
    'author': 'Dekad',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sales_team',
    ],
    'data': [
        # 'security/security.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
