from odoo import models, fields, api, _
import re
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    has_discount_line = fields.Boolean(compute='_compute_discount_info', store=False)
    discount_line_name = fields.Char(compute='_compute_discount_info', store=False)
    discount_line_percent = fields.Char(compute='_compute_discount_info', store=False)
    discount_line_amount = fields.Monetary(
        compute='_compute_discount_info',
        store=False,
        currency_field='currency_id'
    )

    @api.depends('order_line')
    def _compute_discount_info(self):
        percent_regex = re.compile(r'(\d+(?:\.\d+)?)\s*%')

        for order in self:
            discount_lines = order.order_line.filtered(
                lambda l: l.product_id and l.product_id.is_discount
            )

            if discount_lines:
                order.has_discount_line = True
                order.discount_line_name = "Discount"

                # Sum the percentages parsed from line.name like "Discount 5.00%"
                total_percent = 0.0
                for line in discount_lines:
                    match = percent_regex.search(line.name or "")
                    if match:
                        try:
                            total_percent += float(match.group(1))
                        except ValueError:
                            pass

                order.discount_line_percent = f"{total_percent:.2f}" if total_percent else ""

                # Always store discount amount as POSITIVE value
                order.discount_line_amount = abs(
                    sum(line.price_subtotal for line in discount_lines)
                )

            else:
                order.has_discount_line = False
                order.discount_line_name = ''
                order.discount_line_percent = ''
                order.discount_line_amount = 0.0


    def handle_order_names (self) :

        for order in self.search([]):
            if ' - ' in order.name:
                old_name = order.name
                new_name = old_name.split(' - ', 1)[1]

                order.name = new_name
                print(f"Fixed: {old_name} → {new_name}")



    def action_confirm(self):

        for order in self:

            # Company setting disabled
            if not order.company_id.enable_sale_cost_validation:
                continue

            user = self.env.user

            # Apply validation ONLY for pure salesperson
            if (
                user.has_group('sales_team.group_sale_salesman')
                and not user.has_group('sales_team.group_sale_manager')
                and not user.has_group('sales_team.group_sale_salesman_all_leads')
            ):

                total_cost = sum(
                    line.product_id.standard_price * line.product_uom_qty
                    for line in order.order_line
                    if not line.display_type
                )

                if total_cost > order.amount_untaxed:

                    raise ValidationError(_(
                        "You cannot confirm this quotation because "
                        "the total cost is greater than the untaxed amount.\n\n"
                        "Total Cost: %(cost).2f\n"
                        "Untaxed Amount: %(sale).2f"
                    ) % {
                        'cost': total_cost,
                        'sale': order.amount_untaxed,
                    })

        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_image = fields.Binary(
        string="Image",
        compute="_compute_product_image",
        store=True,
        max_width=512,
        max_height=512,
    )

    @api.depends('product_id', 'product_id.image_1920')
    def _compute_product_image(self):
        for line in self:
            line.product_image = line.product_id.image_1920 or line.product_id.product_tmpl_id.image_1920

    def handle_old_order_line_images(self):
        for line in self.search([]):
            line.product_image = line.product_id.image_1920 or line.product_id.product_tmpl_id.image_1920
