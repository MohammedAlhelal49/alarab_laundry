# -*- coding: utf-8 -*-
###############################################################################
#
#    SyncCode Inc
#    Copyright (C) 2009-TODAY SyncCode Inc(<http://www.synccode.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################


# < div
#
#
# class ="alert alert-warning" role="alert" colspan="2" attrs="{'invisible': [('user_group_warning', '=', False)]}" >
#
# < label
# for ="user_group_warning" string="Access Rights Mismatch" class ="text text-warning fw-bold" / >
# < field
# name = "user_group_warning" / >
# < / div >

import logging
import contextlib
from odoo.addons.auth_signup.models.res_partner import now

from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = "res.users"

    def handle_client_company_data(self):
        # handle the system group settings permission

        admin_config_settings = self.env.ref('base.access_res_config_settings')

        admin_config_settings.write({'perm_read': False})

        # reset the old client deploy module customizations

        # delete the new admin client user
        new_admin_user = self.env['res.users'].search([('login', '=', 'admin')])
        settings_group = self.env.ref('base.group_system')
        if new_admin_user :
           settings_group.users = [(4, new_admin_user.id)]

        dekad_user = self.env['res.users'].search([('login', '=', 'dekad')])
        if dekad_user:
            support_group = self.env.ref('dekad_super_user.group_de_support')
            support_group.users = [(4, dekad_user.id)]
        # reset the old client deploy module customizations

        support_group = self.env.ref('dekad_super_user.group_de_support')
        support_user = self.env['res.users'].search([('login', '=', 'dekad')])
        if support_user:
            print('support user already exist')
        else:
            support_user = self.env['res.users'].create({
                'email': 'support@dekad.tech',
                'name': 'Dekad admin',
                'login': 'dekad',
                'password': 'dekad'
            })

            if support_group:
                # Add the user to the group
                support_group.users = [(4, support_user.id)]
        try:
            website_menu_record = self.env.ref('website.menu_website_configuration')
            if website_menu_record:
                website_menu = self.env['ir.ui.menu'].browse(website_menu_record.id)
                website_menu.write({
                    'groups_id': [(6, 0, [support_group.id])]
                })

            link_menu_record = self.env.ref('utm.menu_link_tracker_root')
            if link_menu_record:
                link_menu = self.env['ir.ui.menu'].browse(link_menu_record.id)
                link_menu.write({
                    'groups_id': [(6, 0, [support_group.id])]
                })
        except ValueError:
            _logger.warning("website or link tracker modules dosent exist")

        administration_menu_record = self.env.ref('base.menu_administration')
        administration_menu = self.env['ir.ui.menu'].browse(administration_menu_record.id)
        administration_menu.write({
            'groups_id': [(6, 0, [support_group.id])]
        })

        management_menu_record = self.env.ref('base.menu_management')
        management_menu = self.env['ir.ui.menu'].browse(management_menu_record.id)
        management_menu.write({
            'groups_id': [(6, 0, [support_group.id])]
        })

        # handle the users and contacts actions domains
        action = self.env.ref('dekad_super_user.action_res_users_client')
        action_domain = [('id', '!=', support_user.id)]
        action['domain'] = action_domain

        try:
            action = self.env.ref('contacts.action_contacts')
            action_domain = [('id', '!=', support_user.partner_id.id)]
            action['domain'] = action_domain
        except ValueError:
            # Handle the case where the reference is not found
            action = False  # or return an alternative action or message

    @api.model_create_multi
    def create(self, vals_list):
        config_settings = self.env['res.config.settings'].sudo().get_values()
        users_limit = config_settings.get('users_limit')
        users_limit_number = config_settings.get('users_limit_number')
        if users_limit:
            users_length = len(self.env['res.users'].search([
                ('groups_id', 'in',
                 self.env.ref('base.group_user').id), ('id', '!=', self.env.ref('base.user_admin').id)
            ]))

            if users_length == users_limit_number:
                raise UserError(
                    _(f"Users limit of the company exceded the users limit number ({users_limit_number} users) please contact dekad company administration"))
            else:
                users = super(ResUsers, self).create(vals_list)

        else:
            users = super(ResUsers, self).create(vals_list)

        return users
