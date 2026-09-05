from odoo import models, api


class ProfitLossDashboard(models.AbstractModel):
    _name = 'dekad.profit.loss.dashboard'
    _description = 'Profit & Loss Dashboard'

    @api.model
    def get_invoice_profit_report(self, date_from=False, date_to=False):
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ]
        if date_from:
            domain.append(('invoice_date', '>=', date_from))
        if date_to:
            domain.append(('invoice_date', '<=', date_to))
        invoices = self.env['account.move'].search(domain)

        invoice_lines = []
        total_sales = 0.0
        total_cost = 0.0

        for inv in invoices:
            inv_sales = sum(inv.invoice_line_ids.mapped('price_subtotal'))
            inv_cost = 0.0

            for line in inv.invoice_line_ids:
                if line.sale_line_ids:
                    cost_per_unit = line.sale_line_ids[0].purchase_price
                else:
                    cost_per_unit = line.product_id.standard_price
                inv_cost += cost_per_unit * line.quantity

            inv_profit = inv_sales - inv_cost

            invoice_lines.append({
                'invoice_number': inv.name,
                'invoice_date': inv.invoice_date,
                'total_sales': inv_sales,
                'total_cost': inv_cost,
                'total_profit': inv_profit,
            })

            total_sales += inv_sales
            total_cost += inv_cost

        return {
            'invoice_lines': invoice_lines,
            'total_sales': total_sales,
            'total_cost': total_cost,
            'total_gross_profit': total_sales - total_cost,
        }

    @api.model
    def get_expense_report(self, date_from=False, date_to=False):
        domain = [
            ('move_id.state', '=', 'posted'),
            ('account_id.account_type', '=', 'expense'),
        ]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        expense_lines = self.env['account.move.line'].search(domain)

        expense_by_account = {}
        for line in expense_lines:
            account_name = line.account_id.name
            if account_name not in expense_by_account:
                expense_by_account[account_name] = 0.0
            expense_by_account[account_name] += line.debit - line.credit

        expense_list = [
            {'account_name': name, 'amount': amount}
            for name, amount in expense_by_account.items()
        ]

        total_expenses = sum(expense_by_account.values())

        return {
            'expense_lines': expense_list,
            'total_expenses': total_expenses,
        }

    @api.model
    def get_summary(self, date_from=False, date_to=False):
        invoice_data = self.get_invoice_profit_report(date_from, date_to)
        expense_data = self.get_expense_report(date_from, date_to)

        total_sales = invoice_data['total_sales']
        cost_of_goods_sold = invoice_data['total_cost']
        gross_profit = total_sales - cost_of_goods_sold
        total_expenses = expense_data['total_expenses']
        net_profit = gross_profit - total_expenses

        cogs_percentage = (cost_of_goods_sold / total_sales * 100) if total_sales else 0.
        gross_profit_percentage = (gross_profit / total_sales * 100) if total_sales else 0.0
        expense_percentage = (total_expenses / total_sales * 100) if total_sales else 0.0
        net_profit_percentage = (net_profit / total_sales * 100) if total_sales else 0.0

        return {
            'total_sales': total_sales,
            'cost_of_goods_sold': cost_of_goods_sold,
            'cogs_percentage': cogs_percentage,
            'gross_profit': gross_profit,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'gross_profit_percentage': gross_profit_percentage,
            'expense_percentage': expense_percentage,
            'net_profit_percentage': net_profit_percentage,
        }
