
from odoo import models, fields, api
import re



class StockPicking(models.Model):
    _inherit = 'stock.picking'

    product_uom_qty_sum = fields.Float(compute = "_compute_product_uom_qty_sum")
    quantity_sum = fields.Float(compute="_compute_quantity_sum")

    @api.depends('move_ids_without_package')
    def _compute_product_uom_qty_sum(self):
        for rec in self :
            rec.product_uom_qty_sum = sum(rec.move_ids_without_package.mapped('product_uom_qty'))

    @api.depends('move_ids_without_package')
    def _compute_quantity_sum(self):
        for rec in self:
            rec.quantity_sum = sum(rec.move_ids_without_package.mapped('quantity'))


