from odoo import fields, models

class SaleReport(models.Model):
    _inherit = "sale.report"

    amount_delivered = fields.Float(string='Qty Delivered Amount', readonly=True)
    amount_to_deliver = fields.Float(string='Qty To Deliver Amount', readonly=True)
    amount_to_invoice = fields.Monetary(string="Amount To Invoice", readonly=True)
    amount_invoiced = fields.Monetary(string="Amount Invoiced", readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    # ✅ Boolean field instead of Char
    is_down_payment = fields.Boolean(string='Down Payment', readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res.update({
            'amount_delivered': """
                CASE WHEN l.product_id IS NOT NULL THEN SUM(
                    (l.qty_delivered / NULLIF(l.product_uom_qty, 0)) * l.price_total
                    / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END
                    * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END
                ) ELSE 0 END
            """,
            'amount_to_deliver': """
                CASE WHEN l.product_id IS NOT NULL THEN SUM(
                    ((l.product_uom_qty - l.qty_delivered) / NULLIF(l.product_uom_qty, 0)) * l.price_total
                    / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END
                    * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END
                ) ELSE 0 END
            """,
            'amount_to_invoice': """
                SUM(
                    (l.qty_to_invoice / NULLIF(l.product_uom_qty, 0)) * l.price_total
                    / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END
                    * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END
                )
            """,
            'amount_invoiced': """
                SUM(
                    (l.qty_invoiced / NULLIF(l.product_uom_qty, 0)) * l.price_total
                    / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END
                    * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END
                )
            """,
            # ✅ Set always true
            'is_down_payment': "BOOL_OR(l.is_downpayment)"
        })
        return res
