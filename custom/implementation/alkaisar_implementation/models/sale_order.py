from odoo import models, api, _, fields
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        for order in self:

            total_cost = sum(
                line.unit_cost * line.product_uom_qty
                for line in order.order_line
                if not line.display_type
            )
            if total_cost >= order.amount_total:
                if not self.env.user.has_group('sales_team.group_sale_manager'):
                    raise UserError(
                        "Cost is equal to or higher than the selling price. Only Sales Managers can confirm this order.")
                else:
                    order.message_post(
                        body="⚠️ Warning: Cost is equal to or higher than the selling price. You are confirming this order as a Sales Manager."
                    )

        confirm_record = super().action_confirm()
        for order in self:
            for line in order.order_line:
                line_has_no_bom = not self.env['mrp.bom'].search_count([('product_id', '=', line.product_id.id)])
                line_manufacturing_route = 'Manufacture' in line.product_id.route_ids.mapped('name')
                if line_has_no_bom and line.product_id.type != 'service' and line_manufacturing_route:
                    self.env['mrp.bom'].create({
                        'product_id': line.product_id.id, 'code': f'Created from Sale order : {order.name}',
                        'product_tmpl_id': line.product_id.product_tmpl_id.id
                    })

        # Sale customer history logic
        PriceHistory = self.env['sale.customer.price.history']

        for order in self:
            customer = order.partner_id.commercial_partner_id

            for line in order.order_line:
                # Skip non-product or zero-price lines
                if not line.product_id or line.price_unit <= 0:
                    continue

                # Do not update history if the user entered the price manually
                if not line.use_price_from_history:
                    continue

                domain = [
                    ('partner_id', '=', customer.id),
                    ('product_id', '=', line.product_id.id),
                    ('company_id', '=', order.company_id.id),
                ]

                history = PriceHistory.search(domain, limit=1)

                values = {
                    'price_unit': line.price_unit,
                    'date': fields.Datetime.now(),
                }

                if history:
                    history.write(values)
                else:
                    PriceHistory.create({
                        'partner_id': customer.id,
                        'product_id': line.product_id.id,
                        'price_unit': line.price_unit,
                        'date': fields.Datetime.now(),
                        'company_id': order.company_id.id,
                    })

        return confirm_record

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        if 'partner_id' in fields_list:
            param = self.env['ir.config_parameter'].sudo().get_param(
                'sale.sale_customer_id'
            )
            if param:
                res['partner_id'] = int(param)

        return res
