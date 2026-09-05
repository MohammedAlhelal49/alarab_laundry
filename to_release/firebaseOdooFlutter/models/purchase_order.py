import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        """Override to send FCM notification when a purchase order is confirmed."""
        res = super(PurchaseOrder, self).button_confirm()
        for order in self:
            self._send_purchase_order_notification(order, event='confirmed')
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Send FCM notification when a new purchase order is created."""
        orders = super(PurchaseOrder, self).create(vals_list)
        for order in orders:
            self._send_purchase_order_notification(order, event='created')
        return orders

    def _send_purchase_order_notification(self, order, event='created'):
        """Send FCM notification to relevant users for a purchase order event."""
        recipients = self.env['res.partner']

        # Notify the responsible user
        if order.user_id and order.user_id.partner_id:
            recipients |= order.user_id.partner_id

        # Notify followers
        if order.message_follower_ids:
            for follower in order.message_follower_ids:
                if follower.partner_id:
                    recipients |= follower.partner_id

        # Exclude the current user
        current_partner = self.env.user.partner_id
        if current_partner:
            recipients -= current_partner

        if not recipients:
            return

        if event == 'confirmed':
            title = f"Purchase Order Confirmed: {order.name}"
            body = f"Purchase order {order.name} from {order.partner_id.name or 'N/A'} has been confirmed. Total: {order.amount_total:.2f} {order.currency_id.name or ''}"
        else:
            title = f"New Purchase Order: {order.name}"
            body = f"A new purchase order {order.name} has been created from {order.partner_id.name or 'N/A'}. Total: {order.amount_total:.2f} {order.currency_id.name or ''}"

        fcm_data = {
            "type": "purchase_order",
            "event": event,
            "model": "purchase.order",
            "res_id": str(order.id),
            "record_name": str(order.name or ''),
            "body": body,
        }

        try:
            self.env['mail.thread'].sudo()._send_fcm_common(recipients, title, body, fcm_data)
        except Exception as e:
            _logger.error(f"Failed to send FCM for purchase order {order.name}: {e}")
