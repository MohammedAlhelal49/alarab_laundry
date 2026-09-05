from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class MobileAppController(http.Controller):

    @http.route('/mobile/allowed_apps', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def get_allowed_apps(self, **kwargs):
        """
        Retrieves the list of mobile sub-apps that are active and accessible
        to the currently authenticated user based on their security groups.
        """
        try:
            user = request.env.user
            _logger.info("Fetching allowed mobile apps for user: %s (ID: %s)", user.name, user.id)
            
            # Retrieve all globally active mobile application configurations
            active_apps = request.env['mobile.app.config'].sudo().search([('is_active', '=', True)])
            
            allowed_apps = []
            for app in active_apps:
                # Check access
                if not app.allowed_group_ids and not app.allowed_user_ids:
                    # If no groups and no users are specified, the app is open to all authenticated users
                    has_access = True
                else:
                    has_access = False
                    # 1. Check direct user selection (or via employee relation)
                    if user in app.allowed_user_ids:
                        has_access = True
                    
                    # 2. Check group-based permissions if not already authorized
                    if not has_access and app.allowed_group_ids:
                        for group in app.allowed_group_ids:
                            xml_id = group.get_external_id()
                            if xml_id:
                                # Try matching using the full xml_id (e.g. 'mobile_app_portal.group_mobile_barcode')
                                group_xml_id = xml_id[group.id]
                                if user.has_group(group_xml_id):
                                    has_access = True
                                    break
                            else:
                                # Fallback check
                                if user.has_group(f"{group.category_id.xml_id}.{group.name}"):
                                    has_access = True
                                    break
                
                if has_access:
                    allowed_apps.append({
                        'id': app.id,
                        'name': app.name,
                        'technical_name': app.technical_name,
                        'icon': app.icon,
                        'description': app.description or '',
                    })
            
            return {
                'status': 'success',
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'login': user.login,
                },
                'allowed_apps': allowed_apps
            }
        except Exception as e:
            _logger.error("Error fetching allowed mobile apps: %s", str(e))
            return {
                'status': 'error',
                'message': str(e)
            }
