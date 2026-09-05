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


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    users_limit = fields.Boolean(string="Users limit", default=True)
    users_limit_number = fields.Integer(string="Limit number", default=30)

    @api.constrains('users_limit_number')
    def check_users_limit_number(self):
        users_length = len(self.env['res.users'].search([
            ('groups_id', 'in', self.env.ref('base.group_user').id),
            ('id', '!=', self.env.ref('base.user_admin').id)
        ]))
        for rec in self:
            if rec.users_limit and rec.users_limit_number <= 0:
                raise ValidationError('Please enter a proper Users limit number')
            if rec.users_limit and rec.users_limit_number < users_length:
                raise ValidationError(f'Users limit number is less than the current users number ({users_length})')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        # Save your custom settings in the system parameters
        self.env['ir.config_parameter'].set_param('dekad_super_user.users_limit', self.users_limit)
        self.env['ir.config_parameter'].set_param('dekad_super_user.users_limit_number', self.users_limit_number)

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        # Retrieve your custom settings from the system parameters
        res.update(
            users_limit=self.env['ir.config_parameter'].get_param('dekad_super_user.users_limit', default=True),
            users_limit_number=int(self.env['ir.config_parameter'].get_param('dekad_super_user.users_limit_number', default=10))
        )
        return res