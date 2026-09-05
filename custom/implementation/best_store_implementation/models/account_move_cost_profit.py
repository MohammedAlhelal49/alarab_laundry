# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    total_cost = fields.Float(
        string='Total Cost',
        compute='_compute_cost_and_profit',
        store=True,
        digits='Product Price',
        groups='best_store_implementation.group_show_cost_profit',
        help='Total cost of all products in this invoice based on product cost price.'
    )

    profit = fields.Float(
        string='Profit',
        compute='_compute_cost_and_profit',
        store=True,
        digits='Product Price',
        groups='best_store_implementation.group_show_cost_profit',
        help='Profit = Total Amount (excl. tax) - Total Cost'
    )

    profit_margin = fields.Float(
        string='Profit Margin (%)',
        compute='_compute_cost_and_profit',
        store=True,
        digits=(5, 2),
        groups='best_store_implementation.group_show_cost_profit',
        help='Profit margin percentage'
    )

    @api.depends('invoice_line_ids.quantity', 'invoice_line_ids.price_subtotal',
                 'invoice_line_ids.product_id', 'invoice_line_ids.product_id.standard_price',
                 'amount_untaxed', 'move_type')
    def _compute_cost_and_profit(self):
        for move in self:
            total_cost = 0.0
            if move.move_type in ('out_invoice', 'out_refund'):
                for line in move.invoice_line_ids:
                    if line.product_id and line.display_type == 'product':
                        cost_price = line.product_id.standard_price or 0.0
                        qty = line.quantity or 0.0
                        total_cost += cost_price * qty

                move.total_cost = total_cost
                amount_untaxed = move.amount_untaxed or 0.0

                if move.move_type == 'out_refund':
                    move.profit = total_cost - amount_untaxed
                else:
                    move.profit = amount_untaxed - total_cost

                if amount_untaxed > 0:
                    move.profit_margin = (move.profit / amount_untaxed) * 100
                else:
                    move.profit_margin = 0.0
            else:
                move.total_cost = 0.0
                move.profit = 0.0
                move.profit_margin = 0.0


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    line_cost = fields.Float(
        string='Cost',
        compute='_compute_line_cost',
        store=True,
        digits='Product Price',
        groups='best_store_implementation.group_show_cost_profit',
        help='Cost of this line (Product Cost × Quantity)'
    )

    line_profit = fields.Float(
        string='Line Profit',
        compute='_compute_line_cost',
        store=True,
        digits='Product Price',
        groups='best_store_implementation.group_show_cost_profit',
        help='Profit of this line'
    )

    @api.depends('product_id', 'quantity', 'price_subtotal', 'product_id.standard_price')
    def _compute_line_cost(self):
        for line in self:
            if line.product_id and line.display_type == 'product':
                cost_price = line.product_id.standard_price or 0.0
                qty = line.quantity or 0.0
                line.line_cost = cost_price * qty
                line.line_profit = (line.price_subtotal or 0.0) - line.line_cost
            else:
                line.line_cost = 0.0
                line.line_profit = 0.0