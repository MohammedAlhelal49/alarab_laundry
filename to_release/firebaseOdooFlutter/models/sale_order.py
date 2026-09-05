import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Override to send FCM notification when a sale order is confirmed."""
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            self._send_sale_order_notification(order, event='confirmed')
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Send FCM notification when a new sale order is created."""
        orders = super(SaleOrder, self).create(vals_list)
        for order in orders:
            self._send_sale_order_notification(order, event='created')
        return orders

    def _send_sale_order_notification(self, order, event='created'):
        """Send FCM notification to relevant users for a sale order event."""
        recipients = self.env['res.partner']

        # Notify the salesperson
        if order.user_id and order.user_id.partner_id:
            recipients |= order.user_id.partner_id

        # Notify followers of the sale order
        if order.message_follower_ids:
            for follower in order.message_follower_ids:
                if follower.partner_id:
                    recipients |= follower.partner_id

        # Exclude the current user (the one performing the action)
        # current_partner = self.env.user.partner_id
        # if current_partner:
        #     recipients -= current_partner

        if not recipients:
            return

        if event == 'confirmed':
            title = f"Sale Order Confirmed: {order.name}"
            body = f"Sale order {order.name} for {order.partner_id.name or 'N/A'} has been confirmed. Total: {order.amount_total:.2f} {order.currency_id.name or ''}"
        else:
            title = f"New Sale Order: {order.name}"
            body = f"A new sale order {order.name} has been created for {order.partner_id.name or 'N/A'}. Total: {order.amount_total:.2f} {order.currency_id.name or ''}"

        fcm_data = {
            "type": "sale_order",
            "event": event,
            "model": "sale.order",
            "res_id": str(order.id),
            "record_name": str(order.name or ''),
            "body": body,
        }

        try:
            self.env['mail.thread'].sudo()._send_fcm_common(recipients, title, body, fcm_data)
        except Exception as e:
            _logger.error(f"Failed to send FCM for sale order {order.name}: {e}")
