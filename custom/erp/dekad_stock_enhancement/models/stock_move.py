# -*- coding: utf-8 -*-
from odoo import models,fields,api

class StockMove(models.Model):
    _inherit = "stock.move"

    backup_quantity = fields.Float(string="Backup Quantity", digits='Product Unit of Measure', copy=False)
    backup_product_uom_qty = fields.Float(string="Backup Demand", digits='Product Unit of Measure', copy=False)
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )

    line_index = fields.Integer(
        string="#",
        compute="_compute_line_index",
        store=False
    )

    @api.depends('picking_id.move_ids_without_package.sequence')
    def _compute_line_index(self):
        # group self by picking to compute index relative to the full set on that picking
        for picking in self.mapped('picking_id'):
            moves = picking.move_ids_without_package.sorted('sequence')
            for idx, move in enumerate(moves, start=1):
                if move in self:
                    move.line_index = idx

        # fallback: any record not covered above (e.g. new/unsaved lines
        # not yet linked to picking_id.move_ids_without_package)
        remaining = self.filtered(lambda m: not m.line_index)
        for idx, move in enumerate(remaining, start=1):
            move.line_index = idx


    def _account_entry_move(self, qty, description, svl_id, cost):
        ctx = dict(self.env.context)
        if ctx.get("from_cancel_wizard"):
            ctx["mark_as_cancel_reversal"] = True
        return super(StockMove, self.with_context(ctx))._account_entry_move(
            qty, description, svl_id, cost
        )


