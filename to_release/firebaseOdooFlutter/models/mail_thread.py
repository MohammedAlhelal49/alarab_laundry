import json
import requests
import logging
from collections import defaultdict

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_thread(self, message, msg_vals=None, **kwargs):
        """Override to trigger FCM push notifications."""
        res = super(MailThread, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)
        self._send_fcm_notifications(message)
        return res

    @api.model
    def _send_fcm_notifications(self, message, force_recipients=None):
        """Logic to send FCM notifications for messages."""
        # Use provided recipients or default to message partners (followers/mentions)
        recipients = force_recipients if force_recipients is not None else message.partner_ids
        
        # If no forced recipients, add System Admin and Creator (to maintain functionality from removed mail_message override)
        if force_recipients is None:
            # 1. System admin
            admin_user = self.env.ref('base.user_admin', raise_if_not_found=False)
            if admin_user and admin_user.partner_id:
                recipients |= admin_user.partner_id
                
            # 2. User who created the action (if different from author)
            if message.create_uid and message.create_uid.partner_id:
                recipients |= message.create_uid.partner_id
        
        # Avoid notifying the author of the message
        # if message.author_id:
        #     recipients -= message.author_id

        if not recipients:
            return

        body = tools.html2plaintext(message.body or '')
        title = f"New message from {message.author_id.name or 'Odoo'}"
        if message.record_name:
            title = f"{message.record_name}: {title}"

        fcm_data = {
            "message_id": str(message.id),
            "model": str(message.model),
            "res_id": str(message.res_id),
            "record_name": str(message.record_name or ''),
            "type": "message",
            "body": body,
        }
        
        self._send_fcm_common(recipients, title, body, fcm_data)

    @api.model
    def _send_fcm_activity_notification(self, activity):
        """Logic to send FCM notifications for activities."""
        recipient = activity.user_id.partner_id
        if not recipient:
            return

        title = f"New Activity: {activity.activity_type_id.name or 'Activity'}"
        if activity.res_name:
            title = f"{activity.res_name}: {title}"
        
        body = activity.summary or activity.note or "You have a new activity assigned."
        body = tools.html2plaintext(body)

        fcm_data = {
            "activity_id": str(activity.id),
            "model": str(activity.res_model),
            "res_id": str(activity.res_id),
            "record_name": str(activity.res_name or ''),
            "type": "activity",
            "body": body,
        }
        
        self._send_fcm_common(recipient, title, body, fcm_data)

    @api.model
    def _send_fcm_common(self, recipients, title, body, fcm_data):
        """Common logic to prepare and send FCM notifications to a list of partners."""
        params = self.env['ir.config_parameter'].sudo()
        api_type = params.get_param('firebaseOdooFlutter.api_type', 'legacy')
        custom_data_str = params.get_param('firebaseOdooFlutter.custom_data', '{}')
        
        custom_data = {}
        try:
            if custom_data_str:
                custom_data = json.loads(custom_data_str)
        except Exception:
            _logger.warning("FCM Custom Data is not valid JSON. Ignoring.")

        server_key = params.get_param('firebaseOdooFlutter.server_key') if api_type == 'legacy' else None
        access_token, project_id = None, None
        if api_type != 'legacy':
            service_account_json = params.get_param('firebaseOdooFlutter.service_account')
            if service_account_json:
                try:
                    account_info = json.loads(service_account_json)
                    project_id = account_info.get('project_id')
                    access_token = self._get_fcm_v1_token(account_info)
                except Exception as e:
                    _logger.error(f"FCM v1 Token Error: {e}")
                    return

        # Prepare record and base_url for URL generation
        model = fcm_data.get('model')
        res_id = fcm_data.get('res_id')
        record = None
        if model and res_id and str(res_id).isdigit():
            try:
                record = self.env[model].sudo().browse(int(res_id))
            except Exception:
                pass
        
        base_url = params.get_param('web.base.url')
        delivery_reports = []
        pending_tasks = []

        # 1. Prepare recipients and check access
        for partner in recipients:
            recipient_fcm_data = fcm_data.copy()
            target_user = partner.user_ids[:1]
            has_access = False
            skip_reason = None
            
            if not record or not record.exists():
                has_access = True
            else:
                try:
                    user_record = record.with_user(target_user).sudo(False)
                    if target_user.has_group('base.group_user'):
                        if user_record.has_access('read'):
                            has_access = True
                            recipient_fcm_data['url'] = f"{base_url}/web#id={record.id}&model={record._name}&view_type=form"
                    
                    if not has_access:
                        if record._name == 'sale.order':
                            has_access = True
                            record._portal_ensure_token()
                            recipient_fcm_data['url'] = f"{base_url}/my/orders/{record.id}?access_token={record.access_token}"
                        elif record._name == 'crm.lead':
                            has_access = True
                            if hasattr(record, '_portal_ensure_token'):
                                record._portal_ensure_token()
                            token = getattr(record, 'access_token', '')
                            url_path = record.get_portal_url() if hasattr(record, 'get_portal_url') else f"/my/leads/{record.id}"
                            recipient_fcm_data['url'] = f"{base_url}{url_path}{'?access_token=' + token if token else ''}"
                        elif hasattr(record, 'get_portal_url'):
                            has_access = True
                            if hasattr(record, '_portal_ensure_token'):
                                record._portal_ensure_token()
                            token = getattr(record, 'access_token', '')
                            url_path = record.get_portal_url()
                            full_url = f"{base_url}{url_path}"
                            if token and 'access_token' not in full_url:
                                sep = '&' if '?' in full_url else '?'
                                full_url += f"{sep}access_token={token}"
                            recipient_fcm_data['url'] = full_url
                    
                    if not has_access:
                        skip_reason = "No read access"
                except Exception as e:
                    skip_reason = f"Access check error: {e}"

            if not has_access:
                _logger.info(f"FCM Notification SKIPPED for {partner.name}: {skip_reason or 'No access'}")
                delivery_reports.append(f"<li><b>{partner.name}</b>: <span style='color:orange;'>Skipped</span> ({skip_reason or 'No access'})</li>")
                continue

            # 0. User-level Global Preference check
            model_name = recipient_fcm_data.get('model')
            action_type = recipient_fcm_data.get('event') or recipient_fcm_data.get('type')
            
            if not self.env['fcm.addon.preference'].sudo().is_notification_enabled(partner, model_name, action_type):
                _logger.info(f"FCM Notification SKIPPED for {partner.name}: Disabled per global user preference.")
                delivery_reports.append(f"<li><b>{partner.name}</b>: <span style='color:orange;'>Skipped</span> (Global user preference)</li>")
                continue

            devices = self.env['fcm.device'].sudo().search([('partner_id', '=', partner.id)])
            if not devices:
                _logger.info(f"FCM Notification SKIPPED for {partner.name}: No registered devices found.")
                delivery_reports.append(f"<li><b>{partner.name}</b>: <span style='color:orange;'>Skipped</span> (No registered devices)</li>")
                continue
            
            # Create logs and queue tasks
            for device in devices:
                # 1. Device-specific Preference check
                if not self.env['fcm.addon.preference'].sudo().is_notification_enabled(partner, model_name, action_type, device=device):
                    _logger.info(f"FCM Notification SKIPPED for {partner.name} on device {device.name}: Disabled per device preference.")
                    continue

                log = self.env['fcm.notification'].sudo().create({
                    'partner_id': partner.id,
                    'device_id': device.id,
                    'title': title,
                    'body': body,
                    'res_model': recipient_fcm_data.get('model'),
                    'res_id': int(recipient_fcm_data.get('res_id')) if str(recipient_fcm_data.get('res_id') or '').isdigit() else False,
                    'record_name': recipient_fcm_data.get('record_name'),
                    'notification_type': recipient_fcm_data.get('type'),
                    'click_url': recipient_fcm_data.get('url'),
                    'fcm_data': json.dumps(recipient_fcm_data),
                    'server_url': device.server_url,
                    'dbname': self.env.cr.dbname,
                    'status': 'pending',
                })
                pending_tasks.append({
                    'partner': partner,
                    'device': device,
                    'log': log,
                    'fcm_data': recipient_fcm_data,
                })

        # 2. Group by payload and send in bulk if possible
        grouped_tasks = defaultdict(list)
        for task in pending_tasks:
            key = json.dumps(task['fcm_data'], sort_keys=True)
            grouped_tasks[key].append(task)

        for payload_json, tasks in grouped_tasks.items():
            first_task = tasks[0]
            current_fcm_data = first_task['fcm_data']
            tokens = [t['device'].token for t in tasks]
            
            results = []
            if api_type == 'legacy':
                # Multicast chunking (max 1000)
                for i in range(0, len(tokens), 1000):
                    batch_tokens = tokens[i:i+1000]
                    ok, main_msg, batch_results = self._post_to_fcm_legacy_multicast(batch_tokens, title, body, current_fcm_data, server_key, custom_data)
                    results.extend(batch_results)
            else:
                # v1 remains one-by-one
                for task in tasks:
                    ok, msg = self._post_to_fcm_v1(task['device'].token, title, body, current_fcm_data, access_token, project_id, custom_data)
                    results.append((task['device'].token, ok, msg))

            # 3. Process results and update logs
            # Map results back to tasks (using token and index to handle potential duplicate tokens)
            for (token, ok, msg), task in zip(results, tasks):
                task['log'].write({
                    'status': 'sent' if ok else 'failed',
                    'error_message': msg if not ok else False,
                })
                status_color = "green" if ok else "red"
                status_text = "Sent" if ok else "Failed"
                delivery_reports.append(f"<li><b>{task['partner'].name}</b> ({task['device'].name or 'Device'}): <span style='color:{status_color};'>{status_text}</span> - {msg}</li>")

        # UI Alert
        if delivery_reports and not self.env.su:
            try:
                plain_reports = "\n".join(delivery_reports).replace('<li>', '• ').replace('</li>', '').replace('<b>', '').replace('</b>', '').replace("<span style='color:orange;'>", "").replace("<span style='color:green;'>", "").replace("<span style='color:red;'>", "").replace("</span>", "")
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'notification', {
                    'type': 'success' if "Failed" not in str(delivery_reports) else 'warning',
                    'title': f"FCM: {record.display_name if record else 'Notification'}",
                    'message': plain_reports,
                    'sticky': "Failed" in str(delivery_reports),
                })
            except Exception as e:
                _logger.error(f"Failed to send FCM UI Alert: {e}")

    @api.model
    def _post_to_fcm_legacy_multicast(self, tokens, title, body, fcm_data, server_key, custom_data=None):
        """Legacy FCM HTTP API - Multicast processing."""
        url = "https://fcm.googleapis.com/fcm/send"
        headers = {"Authorization": f"key={server_key}", "Content-Type": "application/json"}
        
        data_payload = fcm_data.copy()
        data_payload.update({
            "notification_title": title,
            "notification_body": body,
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
        })
        if custom_data:
            data_payload.update({str(k): str(v) for k, v in custom_data.items()})

        payload = {"registration_ids": tokens, "data": data_payload, "priority": "high"}
        
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=20)
            if response.status_code in [200, 201]:
                res_json = response.json()
                fcm_results = res_json.get('results', [])
                token_results = []
                for i, token in enumerate(tokens):
                    item = fcm_results[i] if i < len(fcm_results) else {}
                    if 'message_id' in item:
                        token_results.append((token, True, "Successfully sent"))
                    else:
                        token_results.append((token, False, item.get('error', 'Unknown Error')))
                return True, "Batch processed", token_results
            else:
                msg = f"FCM Error {response.status_code}: {response.text}"
                return False, msg, [(t, False, msg) for t in tokens]
        except Exception as e:
            msg = f"Network Error: {str(e)}"
            return False, msg, [(t, False, msg) for t in tokens]

    @api.model
    def _get_fcm_v1_token(self, account_info):
        """Generate OAuth2 token for FCM v1 using Service Account."""
        import time
        import base64
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT"}
        payload = {
            "iss": account_info['client_email'],
            "scope": "https://www.googleapis.com/auth/cloud-platform",
            "aud": "https://oauth2.googleapis.com/token",
            "exp": now + 3600,
            "iat": now
        }

        def base64_url_encode(data):
            return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().strip("=")

        unsigned_token = f"{base64_url_encode(header)}.{base64_url_encode(payload)}"
        
        private_key = serialization.load_pem_private_key(
            account_info['private_key'].encode(),
            password=None
        )
        signature = private_key.sign(
            unsigned_token.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        signed_token = f"{unsigned_token}.{base64.urlsafe_b64encode(signature).decode().strip('=')}"

        # Exchange JWT for Access Token
        url = "https://oauth2.googleapis.com/token"
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": signed_token
        }
        res = requests.post(url, data=data, timeout=10)
        res.raise_for_status()
        return res.json()['access_token']

    @api.model
    def _post_to_fcm_legacy(self, token, title, body, fcm_data, server_key, custom_data=None):
        """Legacy FCM HTTP API - Data-only payload."""
        url = "https://fcm.googleapis.com/fcm/send"
        headers = {
            "Authorization": f"key={server_key}",
            "Content-Type": "application/json"
        }
        
        # Prepare data-only payload
        data_payload = fcm_data.copy()
        data_payload.update({
            "notification_title": title,
            "notification_body": body,
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
        })
        
        if custom_data:
            data_payload.update({str(k): str(v) for k, v in custom_data.items()})

        payload = {
            "to": token,
            "data": data_payload,
            "priority": "high"
        }
        return self._do_post(url, headers, payload)

    @api.model
    def _post_to_fcm_v1(self, token, title, body, fcm_data, access_token, project_id, custom_data=None):
        """Modern FCM HTTP v1 API - Data-only payload."""
        url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Prepare data-only payload
        data_payload = fcm_data.copy()
        data_payload.update({
            "notification_title": title,
            "notification_body": body,
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
        })
        
        if custom_data:
            data_payload.update({str(k): str(v) for k, v in custom_data.items()})

        payload = {
            "message": {
                "token": token,
                "data": data_payload,
                "android": {
                    "priority": "high"
                },
                "apns": {
                    "payload": {
                        "aps": {
                            "content-available": 1
                        }
                    }
                }
            }
        }
        return self._do_post(url, headers, payload)

    @api.model
    def _do_post(self, url, headers, payload):
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                return True, "Successfully sent"
            else:
                return False, f"FCM Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, f"Network Error: {str(e)}"
