from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        # 1. Execute the standard Odoo confirmation process first
        confirm_record = super().action_confirm()

        # 2. MRP Feature: Auto-generate BoM for manufactured products
        for order in self:
            # Check if the feature is enabled for the specific company of the order
            if not order.company_id.auto_create_bom:
                continue

            for line in order.order_line:
                # Check if the product already has a Bill of Materials
                line_has_no_bom = not self.env['mrp.bom'].search_count([
                    ('product_id', '=', line.product_id.id)
                ])

                # Check if the product has the 'Manufacture' route assigned
                line_manufacturing_route = 'Manufacture' in line.product_id.route_ids.mapped('name')

                # Condition: No BoM exists + Not a service + Is a manufactured product
                if line_has_no_bom and line.product_id.type != 'service' and line_manufacturing_route:
                    self.env['mrp.bom'].create({
                        'product_id': line.product_id.id,
                        'product_tmpl_id': line.product_id.product_tmpl_id.id,
                        'code': f'Created from Sale order: {order.name}',
                        'type': 'normal',  # Default to 'Manufacture this product'
                    })

        return confirm_record
