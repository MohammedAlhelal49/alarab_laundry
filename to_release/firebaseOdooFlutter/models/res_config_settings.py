from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fcm_api_type = fields.Selection([
        ('legacy', 'Legacy HTTP API'),
        ('v1', 'HTTP v1 API (Service Account)')
    ], string='FCM API Type', default='legacy', config_parameter='firebaseOdooFlutter.api_type')
    fcm_server_key = fields.Char(string='FCM Server Key (Legacy)', config_parameter='firebaseOdooFlutter.server_key')
    fcm_sender_id = fields.Char(string='FCM Sender ID', config_parameter='firebaseOdooFlutter.sender_id')
    
    # Manual sync for Text fields to avoid Odoo 18 settings limitations with config_parameter
    fcm_service_account = fields.Text(string='Service Account JSON (v1)')
    fcm_custom_data = fields.Text(string='Custom Data (JSON)', 
                                help="Additional JSON data to send with every notification. E.g. {'key': 'value'}")

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            fcm_service_account=params.get_param('firebaseOdooFlutter.service_account'),
            fcm_custom_data=params.get_param('firebaseOdooFlutter.custom_data'),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('firebaseOdooFlutter.service_account', self.fcm_service_account)
        params.set_param('firebaseOdooFlutter.custom_data', self.fcm_custom_data)
