import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    @api.model_create_multi
    def create(self, vals_list):
        activities = super(MailActivity, self).create(vals_list)
        for activity in activities:
            if activity.user_id:
                try:
                    # Notify the assigned user
                    self.env['mail.thread'].sudo()._send_fcm_activity_notification(activity)
                except Exception as e:
                    _logger.error(f"Failed to send FCM notification on activity create: {e}")
        return activities

    def write(self, vals):
        res = super(MailActivity, self).write(vals)
        if 'user_id' in vals:
            for activity in self:
                if activity.user_id:
                    try:
                        # Notify the newly assigned user
                        self.env['mail.thread'].sudo()._send_fcm_activity_notification(activity)
                    except Exception as e:
                        _logger.error(f"Failed to send FCM notification on activity write: {e}")
        return res
