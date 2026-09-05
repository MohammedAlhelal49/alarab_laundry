from odoo import http
from odoo.http import request

class DekadPaymentBanner(http.Controller):

    @http.route('/dekad/banner_message', type='json', auth='user')
    def banner_message(self):
        params = request.env['ir.config_parameter'].sudo()
        enabled = params.get_param('dekad_payment_warning.enable_payment_warning_message') == 'True'
        message = params.get_param('dekad_payment_warning.payment_warning_message') or ''
        excluded_group_ids = params.get_param('dekad_payment_warning.excluded_groups_ids', '')
        excluded_group_ids = [int(gid) for gid in excluded_group_ids.split(',') if gid]

        user = request.env.user


        is_blocked = any(
            group.id in excluded_group_ids for group in user.groups_id
        )

        return {
            'enabled': enabled and not is_blocked,
            'message': message if not is_blocked else '',
        }