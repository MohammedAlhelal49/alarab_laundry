# -*- coding: utf-8 -*-
{
    'name': 'Dekad Intercompany Rules',
    'version': '18.0.3.0.0',
    'category': 'Purchase',
    'summary': 'Enforce intercompany rules: PO lock on SO confirm, receipt quantity lock, tax passthrough, shipment tracking',
    'description': """
Dekad Intercompany Rules
========================

A unified module that enforces intercompany business rules across
Purchase, Sale, Stock and Accounting:

1. PO Lock on SO Confirmation
------------------------------
When Company B confirms the intercompany Sale Order generated from
Company A's Purchase Order, the source PO is automatically locked:
- PO lines become read-only
- Cancel button is disabled
- Unlock button is hidden
When the SO is reset to Draft or cancelled, the PO is unlocked automatically.

2. Receipt Quantity Lock
-------------------------
When a Receipt (incoming picking) is linked to an intercompany Purchase Order,
the done quantity on each move line becomes read-only.
This prevents the buying company from changing the received quantity
after the selling company has validated the delivery.

3. Delivery Cancel Safeguard
------------------------------
Blocks cancelling an intercompany Delivery if the linked Receipt at the
buying company is already Done, and asks the user to contact the buying
company first. If the linked Receipt is only Ready (assigned), it is
automatically reset to Draft and re-assigned to stay in sync.

4. Intercompany Tax Passthrough
---------------------------------
By default, Odoo's inter-company rules modules (sale_purchase_inter_company_rules
and account_inter_company_rules) do NOT copy the taxes from the source document
line to the generated counterpart line. Instead, the generated line always falls
back to the default computed taxes (from the product / fiscal position), even if
the source line had no tax at all.

This module changes that behavior so that the tax configuration is passed through
explicitly:

* Purchase Order line -> generated Sale Order line (other company)
* Sale Order line -> generated Purchase Order line (other company)
* Invoice/Bill line -> generated counterpart Invoice/Bill line (other company)

In every direction:
- If the source line HAS taxes, they are copied as-is to the generated line.
- If the source line has NO taxes (taxes_id / tax_id is empty), the generated
  line is also created with NO taxes, instead of falling back to the default
  computed taxes.

This guarantees that "no tax" on a PO line propagates consistently through the
whole inter-company chain: PO line -> SO line -> Invoice line (and the reverse
SO -> PO direction).

5. Intercompany Shipment Tracking
------------------------------------
Adds shipment tracking fields (Order Confirm Date, Preparing Order Date,
Shipping Order Date, Shipment Delivery Date, Shipment Company, Shipment
Method) on stock.picking, stock.move and stock.move.line.

- Auto-detects Receipts coming from another company (intercompany
  destination) and auto-links them to the matching Delivery.
- Propagates tracking values Header -> Moves -> Move Lines.
- Syncs tracking values from the selling company's Delivery to the buying
  company's linked Receipt (and vice versa via move-level sync), keeping
  intercompany dest records read-only where relevant in the views.
- Auto-fills the Shipping Order Date on Delivery validation and the Order
  Confirm Date on SO confirmation.
- Handles backorders by carrying over only the confirm date and resetting
  the rest of the tracking fields.
    """,
    'author': 'Dekad',
    'website': 'https://www.dekad.co',
    'depends': [
        'purchase',
        'sale',
        'stock',
        'stock_enterprise',
        'sale_stock',
        'purchase_stock',
        'sale_purchase_inter_company_rules',
        'sale_purchase_stock_inter_company_rules',
        'account_inter_company_rules',
        'dekad_stock_enhancement',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_move_views.xml',
        'views/stock_move_line_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
