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

import contextlib

from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import fields, models, _

from odoo.exceptions import UserError

from odoo.addons.auth_signup.models.res_partner import SignupError

# handling the permissions
class ResUsers(models.Model):
    _inherit = "res.users"

    def _action_reset_password(self, signup_type="reset"):
        """ create signup token for each user, and send their signup url by email """
        if self.env.context.get('install_mode') or self.env.context.get('import_file'):
            return
        if self.filtered(lambda user: not user.active):
            raise UserError(_("You cannot perform this action on an archived user."))
        # prepare reset password signup
        create_mode = bool(self.env.context.get('create_user'))

        self.mapped('partner_id').signup_prepare(signup_type=signup_type)

        # send email to users with their signup url
        account_created_template = None
        if create_mode:
            account_created_template = self.env.ref('dekad_addons_enhancement_brand.set_password_email', raise_if_not_found=False)
            if account_created_template and account_created_template._name != 'mail.template':
                _logger.error("Wrong set password template %r", account_created_template)
                return

        email_values = {
            'email_cc': False,
            'auto_delete': True,
            'message_type': 'user_notification',
            'recipient_ids': [],
            'partner_ids': [],
            'scheduled_date': False,
        }

        for user in self:
            if not user.email:
                raise UserError(_("Cannot send email: user %s has no email address.", user.name))
            email_values['email_to'] = user.email
            with contextlib.closing(self.env.cr.savepoint()):
                if account_created_template:
                    account_created_template.send_mail(
                        user.id, force_send=True,
                        raise_exception=True, email_values=email_values)
                else:
                    user_lang = user.lang or self.env.lang or 'en_US'
                    body = self.env['mail.render.mixin'].with_context(lang=user_lang)._render_template(
                        self.env.ref('dekad_addons_enhancement_brand.reset_password_email'),
                        model='res.users', res_ids=user.ids,
                        engine='qweb_view', options={'post_process': True})[user.id]
                    mail = self.env['mail.mail'].sudo().create({
                        'subject': self.with_context(lang=user_lang).env._('Password reset'),
                        'email_from': user.company_id.email_formatted or user.email_formatted,
                        'body_html': body,
                        **email_values,
                    })
                    mail.send()
            if signup_type == 'reset':
                _logger.info("Password reset email sent for user <%s> to <%s>", user.login, user.email)
                message = _('A reset password link was send by email')
            else:
                _logger.info("Signup email sent for user <%s> to <%s>", user.login, user.email)
                message = _('A signup link was send by email')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Notification',
                'message': message,
                'sticky': False
            }
        }

    def send_unregistered_user_reminder(self, after_days=5, batch_size=100):
        email_template = self.env.ref('auth_signup.mail_template_data_unregistered_users', raise_if_not_found=False)
        if not email_template:
            _logger.warning("Template 'auth_signup.mail_template_data_unregistered_users' was not found. Cannot send reminder notifications.")
            return
        datetime_min = fields.Datetime.today() - relativedelta(days=after_days)
        datetime_max = datetime_min + relativedelta(hours=23, minutes=59, seconds=59)

        domain = [('share', '=', False),
            ('create_uid.email', '!=', False),
            ('create_date', '>=', datetime_min),
            ('create_date', '<=', datetime_max),
            ('log_ids', '=', False)]

        res_users_with_details = self.env['res.users'].search_read(domain, ['create_uid', 'name', 'login'], limit=batch_size)

        # group by invited by
        invited_users = defaultdict(list)
        for user in res_users_with_details:
            invited_users[user.get('create_uid')[0]].append("%s (%s)" % (user.get('name'), user.get('login')))

        # For sending mail to all the invitors about their invited users
        for user in invited_users:
            template = email_template.with_context(dbname=self._cr.dbname, invited_users=invited_users[user])
            template.send_mail(user, email_layout_xmlid='mail.mail_notification_light', force_send=False)

        done = len(res_users_with_details)
        self.env['ir.cron']._notify_progress(
            done=done,
            remaining=0 if done < batch_size else self.env['res.users'].search_count(domain)
        )

    def _alert_new_device(self):
        self.ensure_one()
        if self.email:
            email_values = {
                'email_cc': False,
                'auto_delete': True,
                'message_type': 'user_notification',
                'recipient_ids': [],
                'partner_ids': [],
                'scheduled_date': False,
                'email_to': self.email
            }

            body = self.env['mail.render.mixin']._render_template(
                    'auth_signup.alert_login_new_device',
                    model='res.users', res_ids=self.ids,
                    engine='qweb_view', options={'post_process': True},
                    add_context=self._prepare_new_device_notice_values())[self.id]
            mail = self.env['mail.mail'].sudo().create({
                'subject': _('New Connection to your Account'),
                'email_from': self.company_id.email_formatted or self.email_formatted,
                'body_html': body,
                **email_values,
            })
            mail.send()
            _logger.info("New device alert email sent for user <%s> to <%s>", self.login, self.email)
