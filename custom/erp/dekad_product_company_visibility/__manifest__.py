# -*- coding: utf-8 -*-
{
    'name': 'Dekad Product Company Visibility',
    'version': '18.0.2.0.0',
    'category': 'Sales/Inventory',
    'summary': 'Control which products a user can select per company, without touching company_id',
    'description': """
Dekad - Product Company Visibility
===================================
This module allows restricting which products a user can SELECT (search,
autocomplete, "Search More..." dialogs, list/kanban views) for a given
company, without changing the product's underlying company_id field, and
without blocking read access to already-existing documents that reference
the product under a different company.

Why: a product that already has stock moves or accounting entries in more
than one company cannot have its company_id restricted to a single company
(Odoo raises an "Invalid Operation" error). This module solves that by
separating "data ownership" (company_id) from "selection-time visibility"
(company_visibility_id).

- If company_visibility_id is empty => the product can be selected by
  users of any company (same as default Odoo behavior).
- If a company is set => the product can only be found/selected by users
  currently working under one of their active companies.

Design note - IMPORTANT, learned the hard way during testing: this is
implemented via overrides of `name_search()` and `web_search_read()` on
product.template and product.product - NOT `_search()`, and NOT a global
`ir.rule`.

Both `ir.rule` and a `_search()` override were tried and REJECTED, because
Odoo's internal check_access('read') pipeline for a specific already-known
record ID goes through `_search()` (and, transitively, `ir.rule`) itself.
Overriding either one therefore also blocks *reading* a product that is
already referenced by an existing document (Sale Order, Purchase Order,
Stock Picking, etc.) belonging to a different company than the one
currently active - this was reproduced and confirmed twice during testing
(an Access Error when simply opening a historical document).

`name_search()` and `web_search_read()`, by contrast, are top-level RPC
entry points called explicitly by the web client for search/autocomplete
purposes - they are NOT part of the internal read-access-check pipeline,
so overriding them only narrows what appears in NEW search results/dropdowns,
and never affects reading a record whose ID is already known (e.g. a line
on an existing order). Confirmed via testing to cover:
- name_search: standard Many2one dropdowns (Sale Order Line's
  `sol_product_many2one` widget included - it fires one name_search call
  when the dropdown opens, then filters locally as the user types), and
  any plain Many2one field with no custom widget (e.g. hr.expense).
- web_search_read: the "Search More..." full list dialog, and standard
  List/Kanban view data fetching (e.g. the main Sales/Purchase/Inventory
  "Products" screens), which also relies on web_search_read.
    """,
    'author': 'Dekad',
    'depends': ['product', 'hr_expense', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/product_actions.xml',
        'views/product_company_visibility_add_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
