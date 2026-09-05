import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """Override to send FCM notification when a transfer is validated/done."""
        res = super(StockPicking, self).button_validate()
        for picking in self:
            if picking.state == 'done':
                self._send_picking_notification(picking, event='done')
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Send FCM notification when a new transfer is created."""
        pickings = super(StockPicking, self).create(vals_list)
        for picking in pickings:
            self._send_picking_notification(picking, event='created')
        return pickings

    def _send_picking_notification(self, picking, event='created'):
        """Send FCM notification to relevant users for a stock picking event."""
        recipients = self.env['res.partner']

        # Map picking type codes to labels
        type_labels = {
            'incoming': 'Receipt',
            'outgoing': 'Delivery',
            'internal': 'Internal Transfer',
        }
        doc_type = type_labels.get(picking.picking_type_code, 'Transfer')

        # Notify the responsible user
        if picking.user_id and picking.user_id.partner_id:
            recipients |= picking.user_id.partner_id

        # Notify followers
        if picking.message_follower_ids:
            for follower in picking.message_follower_ids:
                if follower.partner_id:
                    recipients |= follower.partner_id

        # Exclude the current user
        current_partner = self.env.user.partner_id
        if current_partner:
            recipients -= current_partner

        if not recipients:
            return

        partner_name = picking.partner_id.name or 'N/A'

        if event == 'done':
            title = f"{doc_type} Done: {picking.name}"
            body = f"{doc_type} {picking.name} ({partner_name}) has been validated."
        else:
            title = f"New {doc_type}: {picking.name}"
            body = f"A new {doc_type.lower()} {picking.name} has been created for {partner_name}."

        fcm_data = {
            "type": "stock_picking",
            "event": event,
            "picking_type": str(picking.picking_type_code or ''),
            "model": "stock.picking",
            "res_id": str(picking.id),
            "record_name": str(picking.name or ''),
            "body": body,
        }

        try:
            self.env['mail.thread'].sudo()._send_fcm_common(recipients, title, body, fcm_data)
        except Exception as e:
            _logger.error(f"Failed to send FCM for {doc_type} {picking.name}: {e}")
