from odoo import fields, models

class FcmDevice(models.Model):
    _name = 'fcm.device'
    _description = 'FCM Device'

    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade', index=True)
    name = fields.Char(string='Device Name', help='e.g., ')
    token = fields.Char(string='FCM Token', required=True, index=True)
    device_type = fields.Selection([
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    ], string='Device Type', default='android')
    dbname = fields.Char(string='Database Name', help='Odoo database name')
    server_url = fields.Char(string='Server URL', help='Odoo server base URL')
    fcm_addon_preference_ids = fields.One2many('fcm.addon.preference', 'device_id', string='Addon Preferences')

    def action_initialize_fcm_preferences(self):
        """Pre-populate preferences for all installed modules and their actions for this device."""
        self.ensure_one()
        installed_modules = self.env['ir.module.module'].search([('state', '=', 'installed')])
        
        for module in installed_modules:
            pref = self.env['fcm.addon.preference'].sudo().search([
                ('device_id', '=', self.id),
                ('module_id', '=', module.id)
            ], limit=1)
            
            if not pref:
                pref = self.env['fcm.addon.preference'].sudo().create({
                    'device_id': self.id,
                    'module_id': module.id,
                    'is_enabled': True
                })
            
            # Initialize actions for this module
            available_actions = pref.get_available_actions(module.name)
            if available_actions:
                existing_action_types = pref.action_ids.mapped('action_type')
                for action_type, action_label in available_actions:
                    if action_type not in existing_action_types:
                        self.env['fcm.addon.preference.action'].sudo().create({
                            'preference_id': pref.id,
                            'action_type': action_type,
                            'action_label': action_label,
                            'is_enabled': True
                        })
                    else:
                        # Update label if it changed or was missing
                        action = pref.action_ids.filtered(lambda a: a.action_type == action_type)
                        if action and not action.action_label:
                            action.write({'action_label': action_label})
        return True

    _sql_constraints = [
        ('token_server_unique', 'unique(token, server_url)', 'The FCM token must be unique per server URL!')
    ]

    def action_test_notification(self):
        """Send a test notification to this specific device (Data-only)."""
        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()
        api_type = params.get_param('firebaseOdooFlutter.api_type', 'legacy')
        custom_data_str = params.get_param('firebaseOdooFlutter.custom_data', '{}')
        
        custom_data = {}
        try:
            if custom_data_str:
                import json
                custom_data = json.loads(custom_data_str)
        except Exception:
            pass
        
        # Prepare data-only payload data
        data_payload = {
            "notification_title": "  Test Connection",
            "notification_body": f"Successful test from Odoo to {self.name or 'Device'}",
            "type": "test",
            "click_action": "FLUTTER_NOTIFICATION_CLICK"
        }
        if custom_data:
            data_payload.update({str(k): str(v) for k, v in custom_data.items()})

        if api_type == 'legacy':
            server_key = params.get_param('firebaseOdooFlutter.server_key')
            if not server_key:
                return self._show_error("FCM Server Key is not configured for Legacy API.")
            url = "https://fcm.googleapis.com/fcm/send"
            headers = {
                "Authorization": f"key={server_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "to": self.token,
                "data": data_payload,
                "priority": "high"
            }
        else:
            service_account_json = params.get_param('firebaseOdooFlutter.service_account')
            if not service_account_json:
                return self._show_error("FCM Service Account is not configured for v1 API.")
            try:
                import json
                account_info = json.loads(service_account_json)
                project_id = account_info.get('project_id')
                access_token = self.env['mail.thread']._get_fcm_v1_token(account_info)
                url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "message": {
                        "token": self.token,
                        "data": data_payload,
                        "android": {"priority": "high"},
                        "apns": {
                            "payload": {
                                "aps": {"content-available": 1}
                            }
                        }
                    }
                }
            except Exception as e:
                return self._show_error(f"FCM v1 Token Error: {e}")

        # Create notification log BEFORE sending
        notification_log = self.env['fcm.notification'].sudo().create({
            'partner_id': self.partner_id.id if self.partner_id else self.env.user.partner_id.id,
            'device_id': self.id,
            'title': data_payload.get('notification_title'),
            'body': data_payload.get('notification_body'),
            'notification_type': 'test',
            'fcm_data': json.dumps(data_payload),
            'server_url': self.server_url,
            'dbname': self.env.cr.dbname,
            'status': 'pending',
        })

        try:
            import requests
            import json
            response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=10)
            success = response.status_code in [200, 201]
            msg = "Successfully sent" if success else f'Google response: {response.text}'
            
            # Update the notification log with the result
            notification_log.write({
                'status': 'sent' if success else 'failed',
                'error_message': msg if not success else False,
            })

            if success:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': 'Test notification sent successfully.',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                return self._show_error(msg)
        except Exception as e:
            error_msg = str(e)
            notification_log.write({
                'status': 'failed',
                'error_message': error_msg,
            })
            return self._show_error(error_msg)

    def _show_error(self, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'FCM Error',
                'message': message,
                'type': 'danger',
                'sticky': True,
            }
        }

class ResPartner(models.Model):
    _inherit = 'res.partner'

    fcm_device_ids = fields.One2many('fcm.device', 'partner_id', string='FCM Devices')
