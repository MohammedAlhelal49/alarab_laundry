from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from pytz import timezone
from datetime import datetime


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        # ==========================================
        # 2) CHECK MAX UNVALIDATED DELIVERIES
        # ==========================================
        enable_max_unvalidated_deliveries = \
            self.env.company.enable_max_unvalidated_deliveries
        max_unvalidated_deliveries = \
            self.env.company.max_unvalidated_deliveries

        if enable_max_unvalidated_deliveries and \
                max_unvalidated_deliveries > 0:

            user = self.env.user
            user_orders = self.search([("user_id", "=", user.id)])
            pickings = user_orders.mapped("picking_ids")

            unvalidated = pickings.filtered(
                lambda p: p.picking_type_code == "outgoing"
                          and p.state != "done"
            )

            if len(unvalidated) >= max_unvalidated_deliveries:
                raise ValidationError(_(
                    "You cannot validate a new Sale Order because you have "
                    "%s unvalidated deliveries."
                ) % len(unvalidated))

        # ==========================================
        # 3) CONFIRM SALE ORDER (STANDARD FLOW)
        # ==========================================
        res = super().action_confirm()

        # ==========================================
        # 4) DIRECT DELIVERY + INVOICE FLOW
        # ==========================================
        company = self.env.company
        direct_sale_delivery_invoice = \
            company.direct_sale_delivery_invoice
        direct_sale_delivery_invoice_state = \
            company.direct_sale_delivery_invoice_state
        direct_sale_delivery_delivery_state = \
            company.direct_sale_delivery_delivery_state

        for order in self:

            delivery_invoice_policy = order.order_line.filtered(
                lambda rec: rec.product_id.invoice_policy == 'delivery'
            )

            if (
                    delivery_invoice_policy
                    and direct_sale_delivery_invoice
                    and direct_sale_delivery_delivery_state == 'draft'
            ):
                order.message_post(
                    body=_(
                        "Direct sale delivery/invoice was skipped because "
                        "one or more products use an invoice policy based on delivered quantities."
                    ),
                    subtype_xmlid="mail.mt_note",
                )
                continue

            if direct_sale_delivery_invoice:

                # Validate delivery automatically
                if direct_sale_delivery_delivery_state == 'validated':
                    deliveries = order.picking_ids
                    for delivery in deliveries:
                        for delivery_item in delivery.move_ids_without_package :
                            delivery_item.quantity = delivery_item.product_uom_qty
                    deliveries.button_validate()

                # Create invoice
                invoices = order._create_invoices()

                # Post invoice automatically
                if invoices and \
                        direct_sale_delivery_invoice_state == 'posted':
                    invoices.write({
                        "invoice_date": datetime.now().astimezone(
                            timezone("Asia/Dubai")
                        )
                    })
                    invoices.action_post()

        return res

    def action_send_whatsapp(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "send.whatsapp.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_sale_order_id": self.id,
                "default_template_id": self.env.ref("dekad_sale_enhancement.whatsapp_quotation_template").id,
            },
        }
