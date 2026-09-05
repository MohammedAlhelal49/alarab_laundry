from odoo import fields, models, api
import json

class FcmNotification(models.Model):
    _name = 'fcm.notification'
    _description = 'FCM Notification Log'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string='Recipient', required=True, ondelete='cascade', index=True)
    device_id = fields.Many2one('fcm.device', string='Device', ondelete='cascade')
    title = fields.Char(string='Title')
    body = fields.Text(string='Body')
    
    # Detailed Data fields
    res_model = fields.Char(string='Model', index=True)
    res_id = fields.Integer(string='Resource ID', index=True)
    record_name = fields.Char(string='Record Name')
    notification_type = fields.Char(string='Notification Type', index=True)
    click_url = fields.Char(string='Click URL')
    
    fcm_data = fields.Text(string='FCM Data (JSON)', help='Raw data payload sent to FCM')
    server_url = fields.Char(string='Server URL', help='Odoo server base URL')
    dbname = fields.Char(string='Database Name', help='Odoo database name')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ], string='Status', default='pending')
    error_message = fields.Text(string='Error Message')
    
    @api.model
    def get_notifications_by_user_id(self, user_id):
        """Fetch notifications for a specific user ID."""
        user = self.env['res.users'].sudo().browse(int(user_id))
        if not user.exists():
            return []
            
        notifications = self.search([('partner_id', '=', user.partner_id.id)], limit=50)
        return [{
            'id': n.id,
            'title': n.title,
            'body': n.body,
            'res_model': n.res_model,
            'res_id': n.res_id,
            'record_name': n.record_name,
            'type': n.notification_type,
            'url': n.click_url,
            'fcm_data': n.fcm_data,
            'status': n.status,
            'create_date': n.create_date,
        } for n in notifications]
