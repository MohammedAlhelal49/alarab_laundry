from odoo import http, api, SUPERUSER_ID
from odoo.http import request
from odoo.modules.registry import Registry
import odoo
import logging

_logger = logging.getLogger(__name__)

class FcmController(http.Controller):
    def __init__(self):
        super().__init__()
        _logger.info("FCM Controller Initialized")

    @http.route('/firebaseOdooFlutter/select_db', type='json', auth='none', methods=['POST'], csrf=False)
    def select_db(self, db=None, **kwargs):
        """Endpoint to select a database and bind it to the session."""
        if not db:
            return {'status': 'error', 'message': 'Database name (db) is required'}
        
        try:
            # Set the database for the session
            request.session.db = db
            # Force session to be saved
            request.session.rotate()
            _logger.info("Database %s selected for session %s", db, request.session.sid)
            return {'status': 'success', 'message': f'Database {db} selected for session'}
        except Exception as e:
            _logger.error("Error selecting database %s: %s", db, str(e))
            return {'status': 'error', 'message': str(e)}

    @http.route('/firebaseOdooFlutter/register_device', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    def register_device(self, token, db=None, device_type='android', device_name=False, user_id=None, server_url=None, **kwargs):
        """Endpoint to register or update an FCM token. Supports multi-database environments."""
        if not token:
            return {'status': 'error', 'message': 'Token is required'}
        
        # Determine which database to use
        db = db or request.params.get('db') or request.httprequest.args.get('db') or request.session.db
        if not db:
            return {'status': 'error', 'message': 'Database (db) is required'}

        # Determine server URL if not provided
        if not server_url:
            server_url = request.httprequest.host_url.rstrip('/')

        try:
            # Bind the DB to session if not already set
            if not request.session.db:
                request.session.db = db

            registry = Registry(db)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                
                partner_id = False
                if user_id:
                    user = env['res.users'].sudo().browse(int(user_id))
                    if user.exists():
                        partner_id = user.partner_id.id

                # Search by token AND server_url to allow same token on different servers
                device = env['fcm.device'].sudo().search([
                    ('token', '=', token),
                    ('server_url', '=', server_url)
                ], limit=1)
                
                vals = {
                    'partner_id': partner_id,
                    'device_type': device_type,
                    'dbname': db,
                    'server_url': server_url,
                }
                if device_name:
                    vals['name'] = device_name
                    
                if device:
                    device.write(vals)
                else:
                    vals['token'] = token
                    env['fcm.device'].create(vals)
                    
                return {'status': 'success', 'message': f'Device registered successfully in {db}'}
        except Exception as e:
            _logger.error("FCM Registration error in %s: %s", db, str(e))
            return {'status': 'error', 'message': f'Database {db} error: {str(e)}'}

    @http.route('/firebaseOdooFlutter/unregister_device', type='json', auth='none', methods=['POST'], csrf=False)
    def unregister_device(self, token, db=None, server_url=None, **kwargs):
        """Endpoint to unregister an FCM token."""
        if not token:
             return {'status': 'error', 'message': 'Token is required'}
        
        db = db or request.params.get('db') or request.httprequest.args.get('db') or request.session.db
        if not db:
            return {'status': 'error', 'message': 'Database (db) is required'}

        if not server_url:
            server_url = request.httprequest.host_url.rstrip('/')

        try:
            registry = Registry(db)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                device = env['fcm.device'].sudo().search([
                    ('token', '=', token),
                    ('server_url', '=', server_url)
                ], limit=1)
                if device:
                    device.unlink()
                return {'status': 'success', 'message': f'Device unregistered successfully from {db}'}
        except Exception as e:
            return {'status': 'error', 'message': f'Database {db} error: {str(e)}'}

    @http.route('/firebaseOdooFlutter/notifications', type='json', auth='none', methods=['POST'], csrf=False)
    def get_notifications(self, user_id, db=None, **kwargs):
        """Endpoint to get notifications for a user."""
        db = db or kwargs.get('db') or request.params.get('db') or request.httprequest.args.get('db') or request.session.db
        if not db:
            return {'status': 'error', 'message': 'Database (db) is required'}
        
        try:
            registry = Registry(db)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                notifications = env['fcm.notification'].sudo().get_notifications_by_user_id(user_id)
                return {'status': 'success', 'data': notifications}
        except Exception as e:
            return {'status': 'error', 'message': f'Database {db} error: {str(e)}'}

    @http.route('/firebaseOdooFlutter/get_preferences', type='json', auth='none', methods=['POST'], csrf=False)
    def get_preferences(self, token, db=None, server_url=None, **kwargs):
        """Endpoint to get notification preferences for a specific device, including granular actions."""
        if not token:
            return {'status': 'error', 'message': 'Token is required'}
        
        db = db or request.params.get('db') or request.httprequest.args.get('db') or request.session.db
        if not db:
            return {'status': 'error', 'message': 'Database (db) is required'}

        if not server_url:
            server_url = request.httprequest.host_url.rstrip('/')

        try:
            registry = Registry(db)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                device = env['fcm.device'].sudo().search([
                    ('token', '=', token),
                    ('server_url', '=', server_url)
                ], limit=1)
                
                if not device:
                    return {'status': 'error', 'message': 'Device not found'}

                # Get all installed modules
                installed_modules = env['ir.module.module'].sudo().search([('state', '=', 'installed')])
                
                # Get existing preferences for this device
                existing_prefs = {p.module_id.id: p for p in device.fcm_addon_preference_ids}

                prefs = []
                for module in installed_modules:
                    pref = existing_prefs.get(module.id)
                    
                    # Get available actions for this module
                    available_actions = env['fcm.addon.preference'].get_available_actions(module.name)
                    
                    actions_data = []
                    if available_actions:
                        # Map existing action preferences
                        existing_actions = {a.action_type: a.is_enabled for a in pref.action_ids} if pref else {}
                        
                        for action_type, action_label in available_actions:
                            actions_data.append({
                                'action_type': action_type,
                                'action_label': action_label,
                                'is_enabled': existing_actions.get(action_type, True) # Default to True
                            })

                    prefs.append({
                        'module_id': module.id,
                        'preference_id': pref.id if pref else False,
                        'module_name': module.name,
                        'module_shortdesc': module.shortdesc,
                        'is_enabled': pref.is_enabled if pref else True, # Default to True if not set
                        'actions': actions_data
                    })
                return {'status': 'success', 'preferences': prefs}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/firebaseOdooFlutter/update_preference', type='json', auth='none', methods=['POST'], csrf=False)
    def update_preference(self, is_enabled, preference_id=None, module_id=None, action_type=None, token=None, db=None, server_url=None, **kwargs):
        """Endpoint to update a specific notification preference or action preference."""
        db = db or request.params.get('db') or request.httprequest.args.get('db') or request.session.db
        if not db:
            return {'status': 'error', 'message': 'Database (db) is required'}

        if not preference_id and not (module_id and token):
            return {'status': 'error', 'message': 'Either preference_id OR (module_id AND token) is required'}

        if not server_url:
            server_url = request.httprequest.host_url.rstrip('/')

        try:
            registry = Registry(db)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                pref = False
                
                if preference_id:
                    pref = env['fcm.addon.preference'].sudo().browse(int(preference_id))
                elif module_id and token:
                    device = env['fcm.device'].sudo().search([
                        ('token', '=', token),
                        ('server_url', '=', server_url)
                    ], limit=1)
                    if not device:
                        return {'status': 'error', 'message': 'Device not found'}
                    
                    pref = env['fcm.addon.preference'].sudo().search([
                        ('device_id', '=', device.id),
                        ('module_id', '=', int(module_id))
                    ], limit=1)
                    
                    if not pref:
                        # Create new preference record if it doesn't exist
                        pref = env['fcm.addon.preference'].sudo().create({
                            'device_id': device.id,
                            'module_id': int(module_id),
                            'is_enabled': True if action_type else bool(is_enabled)
                        })

                if not pref or not pref.exists():
                    return {'status': 'error', 'message': 'Preference not found'}
                
                if action_type:
                    # Update or create action preference
                    action_pref = env['fcm.addon.preference.action'].sudo().search([
                        ('preference_id', '=', pref.id),
                        ('action_type', '=', action_type)
                    ], limit=1)
                    if action_pref:
                        action_pref.write({'is_enabled': bool(is_enabled)})
                    else:
                        env['fcm.addon.preference.action'].sudo().create({
                            'preference_id': pref.id,
                            'action_type': action_type,
                            'is_enabled': bool(is_enabled)
                        })
                    return {'status': 'success', 'message': f'Action preference {action_type} updated'}
                else:
                    # Update main module preference
                    pref.write({'is_enabled': bool(is_enabled)})
                    return {'status': 'success', 'message': 'Module preference updated'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/firebaseOdooFlutter/initialize_preferences', type='json', auth='none', methods=['POST'], csrf=False)
    def initialize_preferences(self, token, db=None, server_url=None, **kwargs):
        """Endpoint to initialize preferences for all installed addons on a device."""
        if not token:
            return {'status': 'error', 'message': 'Token is required'}
        
        db = db or request.params.get('db') or request.httprequest.args.get('db') or request.session.db
        if not db:
            return {'status': 'error', 'message': 'Database (db) is required'}

        if not server_url:
            server_url = request.httprequest.host_url.rstrip('/')

        try:
            registry = Registry(db)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                device = env['fcm.device'].sudo().search([
                    ('token', '=', token),
                    ('server_url', '=', server_url)
                ], limit=1)
                
                if not device:
                    return {'status': 'error', 'message': 'Device not found'}

                device.action_initialize_fcm_preferences()
                return {'status': 'success', 'message': 'Preferences initialized'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


