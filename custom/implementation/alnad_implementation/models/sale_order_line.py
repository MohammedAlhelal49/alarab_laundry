# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.tools.float_utils import float_compare


# ---------------------------------------------------------
# SALE ORDER LINE
# ---------------------------------------------------------
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        if self._context.get("skip_procurement"):
            return True

        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []

        for line in self:
            if line.state != 'sale' or line.product_id.type != 'consu':
                continue

            qty_already = line._get_qty_procurement(previous_product_uom_qty)

            if float_compare(qty_already, line.product_uom_qty, precision_digits=precision) == 0:
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(
                    line._prepare_procurement_group_vals()
                )
                line.order_id.procurement_group_id = group_id

            values = line._prepare_procurement_values(group_id=group_id)

            product_qty = line.product_uom_qty - qty_already

            procurement_uom = line.product_uom

            procurements.append(
                self.env['procurement.group'].Procurement(
                    line.product_id,
                    product_qty,
                    procurement_uom,
                    line._get_location_final(),
                    line.product_id.display_name,
                    line.order_id.name,
                    line.order_id.company_id,
                    values
                )
            )

        if procurements:
            self.env['procurement.group'].run(procurements)

        return True

