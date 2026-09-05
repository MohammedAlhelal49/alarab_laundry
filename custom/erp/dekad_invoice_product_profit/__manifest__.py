{
    "name": "Invoice Profitability Reports",
    "version": "18.0.2.0.0",
    "category": "Accounting/Reporting",
    "summary": "Invoice/product profitability reports, historical cost backfill, and a Profit & Loss dashboard.",
    "description": """
Invoice Profitability Analysis
==============================
Profitability reports based on a cost snapshot frozen at the moment the
customer invoice (or credit note) is confirmed (posted).

Cost capture (reports):
------------------------
* When a customer invoice / credit note is posted, the current
  `product.standard_price` is captured onto each product line as
  `current_cost`. Idempotent - once written it is not overwritten on
  reset-to-draft / re-post.
* Historic invoices posted before the module was installed can be
  backfilled from the stock valuation layers via a wizard under
  Accounting > Reporting > Profitability Analysis > Backfill Historical Costs.

Reports:
--------
* By Invoice - one row per posted customer invoice/credit note, with
  filters to isolate invoices only or credit notes only.
* By Invoice Product(line item) Line - one row per invoice line, fully
  detailed.

Profit & Loss Dashboard:
-------------------------
* An interactive client action showing Total Sales, Cost of Goods Sold,
  Gross Profit, Total Expenses and Net Profit, with an Invoice Profit
  Report / Expense Report breakdown and optional date-range filtering.
* Access is restricted to the "Profit & Loss Dashboard User" security
  group.
* The dashboard computes cost live (from `sale_line_ids.purchase_price`
  when available, otherwise the product's current `standard_price`) at
  the moment it is opened - it does NOT use the frozen snapshot used by
  the reports above. This is intentional.
    """,
    "author": "Dekad",
    "depends": [
        "account",
        "stock_account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/invoice_profit_reports_view.xml",
        "views/dashboard_menu.xml",
        "wizards/backfill_current_cost_wizard_view.xml",
        "views/res_config_settings_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "dekad_invoice_product_profit/static/src/css/dashboard.css",
            "dekad_invoice_product_profit/static/src/js/dashboard.js",
            "dekad_invoice_product_profit/static/src/xml/dashboard.xml",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}