from odoo import models, fields


# ---------------------------------------------------------------------------
# All reports read cost EXCLUSIVELY from aml.current_cost (the frozen
# snapshot captured at the moment of sale). NO fallback to the product's
# current standard_price — falling back would defeat the very point of the
# snapshot. Lines without a snapshot (e.g. invoices created before the
# module was installed) will therefore show profit = revenue.
#
# COALESCE(..., 0) is only used to keep arithmetic safe in the presence of
# NULLs; it is NOT a fallback to live product cost.
# ---------------------------------------------------------------------------


class AccountInvoiceProfitReport(models.Model):
    _name = 'account.report.invoice.profit'
    _description = 'Invoice Profit Report'
    _auto = False

    move_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    ref = fields.Char(string='Reference', readonly=True)
    invoice_date = fields.Date(string='Date', readonly=True)
    invoice_user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    revenue = fields.Float(string='Total Revenue', readonly=True)
    total_cost = fields.Float(string='Total Cost', readonly=True)
    profit = fields.Float(string='Profit', readonly=True)
    profit_percentage = fields.Float(string='Profit %', readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS account_report_invoice_profit CASCADE;")
        self.env.cr.execute("""
            CREATE VIEW account_report_invoice_profit AS (
                SELECT
                    am.id AS id,
                    am.id AS move_id,
                    am.partner_id,
                    am.journal_id,
                    am.ref,
                    am.invoice_date,
                    am.invoice_user_id,
                    am.company_id,
                    SUM(aml.price_subtotal) AS revenue,
                    SUM(aml.quantity * COALESCE(aml.current_cost, 0)) AS total_cost,
                    SUM(aml.price_subtotal - aml.quantity * COALESCE(aml.current_cost, 0)) AS profit,
                    CASE
                        WHEN SUM(aml.price_subtotal) = 0 THEN 0
                        ELSE ROUND(
                            (SUM(aml.price_subtotal - aml.quantity * COALESCE(aml.current_cost, 0)) /
                             NULLIF(SUM(aml.price_subtotal), 0) * 100.0)::numeric,
                            2
                        )
                    END AS profit_percentage
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE am.move_type IN ('out_invoice', 'out_refund')
                  AND aml.display_type = 'product'
                  AND am.state = 'posted'
                GROUP BY
                    am.id,
                    am.partner_id,
                    am.journal_id,
                    am.ref,
                    am.invoice_date,
                    am.invoice_user_id,
                    am.company_id
            )
        """)


class AccountInvoiceLineProfitReport(models.Model):
    _name = 'account.report.invoice.line.profit'
    _description = 'Invoice Product Profit Report'
    _auto = False

    move_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    ref = fields.Char(string='Reference', readonly=True)
    invoice_date = fields.Date(string='Date', readonly=True)
    invoice_user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)
    unit_cost = fields.Float(string='Unit Cost (frozen)', readonly=True)
    revenue = fields.Float(string='Line Revenue', readonly=True)
    total_cost = fields.Float(string='Total Cost', readonly=True)
    profit = fields.Float(string='Profit', readonly=True)
    profit_percentage = fields.Float(string='Profit %', readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS account_report_invoice_line_profit CASCADE;")
        self.env.cr.execute("""
            CREATE VIEW account_report_invoice_line_profit AS (
                SELECT
                    aml.id AS id,
                    aml.move_id,
                    aml.product_id,
                    pt.categ_id AS product_categ_id,
                    am.partner_id,
                    am.journal_id,
                    am.ref,
                    am.invoice_date,
                    am.invoice_user_id,
                    am.company_id,
                    aml.quantity,
                    COALESCE(aml.current_cost, 0) AS unit_cost,
                    aml.price_subtotal AS revenue,
                    (aml.quantity * COALESCE(aml.current_cost, 0)) AS total_cost,
                    (aml.price_subtotal - aml.quantity * COALESCE(aml.current_cost, 0)) AS profit,
                    CASE
                        WHEN aml.price_subtotal = 0 THEN 0
                        ELSE ROUND(
                            ((aml.price_subtotal - aml.quantity * COALESCE(aml.current_cost, 0)) /
                             NULLIF(aml.price_subtotal, 0) * 100.0)::numeric,
                            2
                        )
                    END AS profit_percentage
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                LEFT JOIN product_product pp ON pp.id = aml.product_id
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE am.move_type IN ('out_invoice', 'out_refund')
                  AND aml.display_type = 'product'
                  AND am.state = 'posted'
            )
        """)