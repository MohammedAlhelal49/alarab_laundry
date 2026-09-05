import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class MailMessage(models.Model):
    _inherit = 'mail.message'

    # The create override was removed to avoid double notifications, 
    # as FCM notifications are already handled in mail.thread._notify_thread.
