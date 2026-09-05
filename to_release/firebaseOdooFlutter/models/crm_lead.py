import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model_create_multi
    def create(self, vals_list):
        """Send FCM notification when a new lead/opportunity is created."""
        leads = super(CrmLead, self).create(vals_list)
        for lead in leads:
            self._send_crm_notification(lead, event='created')
        return leads

    def action_set_won_rainbowman(self):
        """Override to send FCM notification when an opportunity is marked as won."""
        res = super(CrmLead, self).action_set_won_rainbowman()
        for lead in self:
            self._send_crm_notification(lead, event='won')
        return res

    def write(self, vals):
        """Send notification when a lead is assigned to a new user."""
        old_users = {lead.id: lead.user_id for lead in self}
        res = super(CrmLead, self).write(vals)
        if 'user_id' in vals:
            for lead in self:
                # Only notify if the user actually changed
                if old_users.get(lead.id) != lead.user_id:
                    self._send_crm_notification(lead, event='assigned')
        return res

    def _send_crm_notification(self, lead, event='created'):
        """Send FCM notification to relevant users for a CRM lead event."""
        recipients = self.env['res.partner']
        doc_type = 'Opportunity' if lead.type == 'opportunity' else 'Lead'

        # Notify the assigned salesperson
        if lead.user_id and lead.user_id.partner_id:
            recipients |= lead.user_id.partner_id

        # Notify the sales team leader
        if lead.team_id and lead.team_id.user_id and lead.team_id.user_id.partner_id:
            recipients |= lead.team_id.user_id.partner_id

        # Notify followers
        if lead.message_follower_ids:
            for follower in lead.message_follower_ids:
                if follower.partner_id:
                    recipients |= follower.partner_id

        # Exclude the current user
        current_partner = self.env.user.partner_id
        if current_partner:
            recipients -= current_partner

        if not recipients:
            return

        partner_name = lead.partner_id.name if lead.partner_id else 'N/A'

        if event == 'won':
            title = f"🎉 {doc_type} Won: {lead.name}"
            body = f"{doc_type} '{lead.name}' ({partner_name}) has been marked as won!"
            if lead.expected_revenue:
                body += f" Revenue: {lead.expected_revenue:.2f}"
        elif event == 'assigned':
            title = f"{doc_type} Assigned: {lead.name}"
            body = f"{doc_type} '{lead.name}' ({partner_name}) has been assigned to {lead.user_id.name}."
        else:
            title = f"New {doc_type}: {lead.name}"
            body = f"A new {doc_type.lower()} '{lead.name}' has been created for {partner_name}."

        fcm_data = {
            "type": "crm_lead",
            "event": event,
            "lead_type": str(lead.type or ''),
            "model": "crm.lead",
            "res_id": str(lead.id),
            "record_name": str(lead.name or ''),
            "body": body,
        }

        try:
            self.env['mail.thread'].sudo()._send_fcm_common(recipients, title, body, fcm_data)
        except Exception as e:
            _logger.error(f"Failed to send FCM for {doc_type} {lead.name}: {e}")
