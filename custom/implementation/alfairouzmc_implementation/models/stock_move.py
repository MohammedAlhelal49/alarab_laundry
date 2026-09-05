# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):

        self._check_negative_stock_restriction()
        return super()._action_done(cancel_backorder=cancel_backorder)

    def _check_negative_stock_restriction(self):
        company = self.env.company

        if not company.restrict_negative_delivery:
            return

        if self.env.user in company.negative_delivery_allowed_user_ids:
            return

        for move in self:

            is_delivery = move.picking_type_id.code == 'outgoing'
            is_to_inventory_loss = move.location_dest_id.usage == 'inventory'

            if not (is_delivery or is_to_inventory_loss):
                continue

            product = move.product_id
            qty_on_hand = product.quantity_on_hand
            qty_to_deliver = move.quantity

            resulting_qty = qty_on_hand - qty_to_deliver

            if resulting_qty < 0:
                raise ValidationError(_(
                    "You are not allowed to move %(qty)s of '%(product)s' out: "
                    "only %(available)s is currently available in stock, and "
                    "this operation would bring the stock on hand to a "
                    "negative value (%(resulting)s). "
                    "Contact your administrator if you need permission to "
                    "output negative stock.",
                    qty=qty_to_deliver,
                    product=product.display_name,
                    available=qty_on_hand,
                    resulting=resulting_qty,
                ))
