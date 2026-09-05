from odoo import api, fields, models
from odoo.tools.sql import SQL


class PurchaseReport(models.Model):
    _inherit = "purchase.report"
    _rec_name = "product_id"
    _order = "order_id, date_order desc, price_total desc"

    amount_received = fields.Float('Amount received')
    amount_to_invoice = fields.Float('Amount to bill')
    amount_invoiced = fields.Float('Amount Billed')
    price_unit = fields.Float(string='Unit Price')

    analytic_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        string='Analytic Accounts',
        compute='_compute_analytic_ids',
        search='_search_analytic_ids',
    )

    @staticmethod
    def _extract_analytic_account_ids(analytic_distribution):
        ids = set()
        for key in (analytic_distribution or {}).keys():
            for part in str(key).split(','):
                try:
                    ids.add(int(part))
                except (ValueError, AttributeError):
                    pass
        return list(ids)

    def _compute_analytic_ids(self):

        if not self.ids:
            return
        rec_keys = set()
        for rec in self:
            if rec.order_id and rec.product_id:
                rec_keys.add((rec.order_id.id, rec.product_id.id))

        if not rec_keys:
            for rec in self:
                rec.analytic_ids = self.env['account.analytic.account']
            return

        order_ids = [k[0] for k in rec_keys]
        product_ids = [k[1] for k in rec_keys]

        lines = self.env['purchase.order.line'].sudo().search([
            ('order_id', 'in', order_ids),
            ('product_id', 'in', product_ids),
            ('analytic_distribution', '!=', False),
        ])

        key_to_accounts = {}
        for line in lines:
            key = (line.order_id.id, line.product_id.id)
            ids = self._extract_analytic_account_ids(line.analytic_distribution)

            accounts = self.env['account.analytic.account'].browse(ids).exists()

            key_to_accounts.setdefault(key, set()).update(accounts.ids)

        for rec in self:
            key = (rec.order_id.id if rec.order_id else None,
                   rec.product_id.id if rec.product_id else None)
            account_ids = list(key_to_accounts.get(key, set()))
            rec.analytic_ids = self.env['account.analytic.account'].browse(account_ids)


    def _search_analytic_ids(self, operator, value):
        if operator in ('=', 'in'):
            account_ids = set(value if isinstance(value, list) else [value])

            lines = self.env['purchase.order.line'].sudo().search([
                ('analytic_distribution', '!=', False)
            ])

            keys = set()
            for line in lines:
                extracted = self._extract_analytic_account_ids(line.analytic_distribution)
                accounts = self.env['account.analytic.account'].browse(extracted).exists()

                if account_ids & set(accounts.ids):
                    keys.add((line.order_id.id, line.product_id.id))

            if not keys:
                return [('id', '=', 0)]

            domain = []
            for order_id, product_id in keys:
                domain.append(('order_id', '=', order_id))
                domain.append(('product_id', '=', product_id))

            return domain

        return [('id', '=', 0)]

    def _select(self) -> SQL:
        return SQL(
            """
                %s,
                sum(l.qty_received / line_uom.factor * product_uom.factor * l.price_unit / COALESCE(po.currency_rate, 1.0))::decimal(16,2) * account_currency_table.rate as amount_received,
                sum(l.qty_invoiced / line_uom.factor * product_uom.factor * l.price_unit / COALESCE(po.currency_rate, 1.0))::decimal(16,2) * account_currency_table.rate as amount_invoiced,
                sum(l.qty_to_invoice / line_uom.factor * product_uom.factor * l.price_unit / COALESCE(po.currency_rate, 1.0))::decimal(16,2) * account_currency_table.rate as amount_to_invoice,
                l.price_unit as price_unit
            """,
            super()._select()
        )

    def _group_by(self) -> SQL:
        return SQL("%s, l.price_unit", super()._group_by())