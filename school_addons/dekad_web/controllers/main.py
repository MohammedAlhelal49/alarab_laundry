# -*- coding: utf-8 -*-
###############################################################################
#
#    Dekad Inc
#    Copyright (C) 2009-TODAY Dekad Inc(<http://www.Dekad.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
# rrrr
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import http
from odoo.http import request
import werkzeug.utils
from odoo.addons.portal.controllers.web import Home as home

from werkzeug.utils import redirect


class DekadHome(home):
    @http.route()
    def web_login(self, redirect=None, *args, **kw):
        response = super(DekadHome, self).web_login(
            redirect=redirect, *args, **kw)
        if not redirect and request.params['login_success']:
            if request.env['res.users'].browse(request.uid).has_group(
                    'base.group_user'):
                redirect ='/web?' + request.httprequest.query_string.decode('utf-8')
            else:
                redirect = '/my'
            return werkzeug.utils.redirect(redirect)
        return response

    def _login_redirect(self, uid, redirect=None):
        if redirect:
            return super(DekadHome, self)._login_redirect(uid, redirect)
        return '/my/home'

    @http.route('/blocked', website=True)
    def blocked_user(self, **kw):
        user = request.env.user
        values = {
            'page_name': 'Blocked user',
            'page_url': '/blocked',

        }
        if not (user and user.is_student and (user.is_suspended or user.is_blocked)):
            return redirect('/')

        return http.request.render('dekad_web.blocked_user', values)
