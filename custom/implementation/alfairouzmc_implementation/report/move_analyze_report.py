# -*- coding: utf-8 -*-
from odoo import models, api
from itertools import groupby
from operator import attrgetter


class MoveAnalyzeReport(models.AbstractModel):
    _name = 'report.alfairouzmc_implementation.report_move_analyze'
    _description = 'Move Analyze Report PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        moves = self.env['stock.move'].browse(docids)

        moves = moves.sorted(
            key=lambda m: (m.analytic_account_id.name or '')
        )

        grouped_data = []
        for account, moves_group in groupby(moves, key=attrgetter('analytic_account_id')):
            lines = list(moves_group)
            grouped_data.append({
                'account': account,  # a recordset (single record or empty)
                'lines': lines,  # the stock.move records in this group
                'total_demand': sum(l.product_uom_qty for l in lines),  # sum for the "Demand" column
                'total_quantity': sum(l.quantity for l in lines),  # sum for the "Quantity" column
            })

        return {
            'doc_ids': docids,
            'doc_model': 'stock.move',
            'docs': moves,
            'grouped_data': grouped_data,
        }
