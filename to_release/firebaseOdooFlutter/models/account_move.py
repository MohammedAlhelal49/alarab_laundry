import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """Override to send FCM notification when an invoice/bill is posted."""
        res = super(AccountMove, self).action_post()
        for move in self:
            self._send_account_move_notification(move, event='posted')
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Send FCM notification when a new invoice/bill is created."""
        moves = super(AccountMove, self).create(vals_list)
        for move in moves:
            # Only notify for customer invoices, vendor bills, credit/debit notes
            if move.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                self._send_account_move_notification(move, event='created')
        return moves

    def _send_account_move_notification(self, move, event='created'):
        """Send FCM notification to relevant users for an invoice/bill event."""
        recipients = self.env['res.partner']

        # Map move types to human-readable labels
        type_labels = {
            'out_invoice': 'Invoice',
            'out_refund': 'Credit Note',
            'in_invoice': 'Vendor Bill',
            'in_refund': 'Debit Note',
            'entry': 'Journal Entry',
        }
        doc_type = type_labels.get(move.move_type, 'Journal Entry')

        # Notify the responsible user (invoice_user_id or user who created it)
        responsible = move.invoice_user_id or move.create_uid
        if responsible and responsible.partner_id:
            recipients |= responsible.partner_id

        # Notify followers
        if move.message_follower_ids:
            for follower in move.message_follower_ids:
                if follower.partner_id:
                    recipients |= follower.partner_id

        # Exclude the current user
        current_partner = self.env.user.partner_id
        if current_partner:
            recipients -= current_partner

        if not recipients:
            return

        if event == 'posted':
            title = f"{doc_type} Posted: {move.name}"
            body = f"{doc_type} {move.name} for {move.partner_id.name or 'N/A'} has been posted. Amount: {move.amount_total:.2f} {move.currency_id.name or ''}"
        else:
            title = f"New {doc_type}: {move.name or 'Draft'}"
            body = f"A new {doc_type.lower()} has been created for {move.partner_id.name or 'N/A'}. Amount: {move.amount_total:.2f} {move.currency_id.name or ''}"

        fcm_data = {
            "type": "account_move",
            "event": event,
            "move_type": str(move.move_type),
            "model": "account.move",
            "res_id": str(move.id),
            "record_name": str(move.name or ''),
            "body": body,
        }

        try:
            self.env['mail.thread'].sudo()._send_fcm_common(recipients, title, body, fcm_data)
        except Exception as e:
            _logger.error(f"Failed to send FCM for {doc_type} {move.name}: {e}")
