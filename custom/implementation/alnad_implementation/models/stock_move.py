# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.tools.float_utils import float_compare

# PURCHASE ORDER LINE
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_stock_moves(self, picking):
        res = super()._prepare_stock_moves(picking)

        for move_vals in res:
            move_vals['product_uom'] = self.product_uom.id
            move_vals['product_uom_qty'] = self.product_qty

        return res


# STOCK MOVE
class StockMove(models.Model):
    _inherit = 'stock.move'

    # Set the move UoM based on source document (Purchase or Sale)
    # This prevents Odoo from defaulting to the product's UoM
    @api.depends('purchase_line_id', 'sale_line_id')
    def _compute_product_uom(self):
        for move in self:
            if move.purchase_line_id:
                move.product_uom = move.purchase_line_id.product_uom
            elif move.sale_line_id:
                move.product_uom = move.sale_line_id.product_uom

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(quantity, reserved_quant)

        # Force move line to use the same UoM as the stock move (no conversion)
        if self.product_uom:
            vals['product_uom_id'] = self.product_uom.id

        return vals