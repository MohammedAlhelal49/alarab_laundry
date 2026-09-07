# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import date, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrEmployeeDocument(models.Model):
    """This class represents HR employee documents and provides methods
    for managing document expiry notifications."""
    _name = 'hr.employee.document'
    _description = 'HR Employee Documents'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Document Number', required=True, copy=False,tracking=True,
                       help='You can give your Document number.')
    description = fields.Text(string='Description', copy=False,
                              help="Description of the documents.")
    expiry_date = fields.Date(string='Expiry Date', copy=False,tracking=True,
                              help="Expiry date of the documents.")
    employee_ref_id = fields.Many2one('hr.employee', invisible=1,
                                      copy=False,tracking=True,
                                      help='Specify the employee name.')
    doc_attachment_ids = fields.Many2many('ir.attachment',
                                          'doc_attach_rel',
                                          'doc_id', 'attach_id3',
                                          string="Attachment",tracking=True,
                                          help='You can attach the copy of your'
                                               ' document', copy=False)
    issue_date = fields.Date(string='Issue Date',required=True,tracking=True,
                             help="Date of issued", copy=False)
    document_type_id = fields.Many2one('document.type',tracking=True,
                                       string="Document Type",
                                       help="Type of the document.")
    before_days = fields.Integer(string="Days",tracking=True,
                                 help="How many number of days before to get "
                                      "the notification email.")
    notification_type = fields.Selection([
        ('single', 'Notification on expiry date'),
        ('multi', 'Notification before few days'),
        ('everyday', 'Everyday till expiry date'),
        ('everyday_after', 'Notification on and after expiry')
    ], string='Notification Type',tracking=True,
        help="Select type of the documents expiry notification.")

    notify_type = fields.Selection([
        ('email', 'Email'),
        ('activity', 'Activity'),
        ('both', 'Both'),
    ], string='Notify Via', default='email', required=True,tracking=True,
        help="Email: sends a reminder email to the document's employee "
             "(current behavior, unchanged).\n"
             "Activity: creates an Odoo Activity assigned to each user "
             "selected in 'Users to Notify'.\n"
             "Both: does both of the above.")

    notify_user_ids = fields.Many2many(
        'res.users', 'hr_employee_document_notify_user_rel',
        'document_id', 'user_id', string='Users to Notify',tracking=True,
        help="Users who will get an Activity reminder. Required when "
             "'Notify Via' is set to Activity or Both.")

    state = fields.Selection([
        ('in_progress', 'In Progress'),
        ('expired', 'Expired'),
    ], string='Status', default='in_progress', required=True,
        copy=False, tracking=True, readonly=True)

    remaining_days = fields.Integer(
        string='Remaining Days',
        compute='_compute_remaining_days',
        readonly=True,
        help='Number of days remaining until the document expires. '
             'Negative values indicate that the document has expired.'
    )

    renewed_from_id = fields.Many2one(
        'hr.employee.document',
        string='Renewed From',
        readonly=True,
        copy=False,
        ondelete='set null',
        help='The expired document from which this document was renewed.'
    )

    renewed_document_ids = fields.One2many(
        'hr.employee.document',
        'renewed_from_id',
        string='Renewed Documents',
        readonly=True,
    )

    renewed_document_count = fields.Integer(
        string='Renewed Documents',
        compute='_compute_renewed_document_count',
    )

    @api.depends('renewed_document_ids')
    def _compute_renewed_document_count(self):
        for record in self:
            record.renewed_document_count = len(
                record.renewed_document_ids
            )

    def action_view_renewed_from(self):
        """Open the original document this document was renewed from."""
        self.ensure_one()

        if not self.renewed_from_id:
            return False

        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewed From'),
            'res_model': 'hr.employee.document',
            'res_id': self.renewed_from_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_renewed_documents(self):
        """Open documents renewed from this document."""
        self.ensure_one()

        documents = self.renewed_document_ids

        if len(documents) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Renewed Document'),
                'res_model': 'hr.employee.document',
                'res_id': documents.id,
                'view_mode': 'form',
                'target': 'current',
            }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewed Documents'),
            'res_model': 'hr.employee.document',
            'view_mode': 'list,form',
            'domain': [('renewed_from_id', '=', self.id)],
            'target': 'current',
        }

    def action_renew_document(self):
        """Open a new document populated from the expired document."""
        self.ensure_one()

        if self.state != 'expired':
            raise UserError(_('Only expired documents can be renewed.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Renew Document'),
            'res_model': 'hr.employee.document',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_employee_ref_id': self.employee_ref_id.id,
                'default_document_type_id': self.document_type_id.id,
                'default_notification_type': self.notification_type,
                'default_before_days': self.before_days,
                'default_notify_type': self.notify_type,
                'default_notify_user_ids': [
                    (6, 0, self.notify_user_ids.ids)
                ],
                'default_renewed_from_id': self.id,

                # Keep the users copied from the expired document
                'skip_default_notify_users': True,
            },
        }


    @api.depends('expiry_date')
    def _compute_remaining_days(self):
        today = fields.Date.context_today(self)

        for record in self:
            if record.expiry_date:
                record.remaining_days = (
                        record.expiry_date - today
                ).days
            else:
                record.remaining_days = 0


    @api.onchange('employee_ref_id')
    def _onchange_employee_ref_id_notify_users(self):
        if self.env.context.get('skip_default_notify_users'):
            return

        if not self.employee_ref_id:
            self.notify_user_ids = [(5, 0, 0)]
            return

        employee = self.employee_ref_id

        users = (
                employee.parent_id.user_id |
                employee.coach_id.user_id |
                employee.pro_id.user_id
        )

        self.notify_user_ids = [(6, 0, users.ids)]

    def _initialize_notify_users(self):
        """Set default notify users only when Users to Notify is empty."""
        documents = self.search([
            ('employee_ref_id', '!=', False),
            ('notify_user_ids', '=', False),
        ])

        for document in documents:
            employee = document.employee_ref_id

            users = (
                    employee.parent_id.user_id |
                    employee.coach_id.user_id |
                    employee.pro_id.user_id
            )

            if users:
                document.write({
                    'notify_user_ids': [(6, 0, users.ids)]
                })

        return True


    def _update_document_state(self):
        """Update document status based on expiry date."""
        today = fields.Date.context_today(self)

        expired_records = self.search([
            ('expiry_date', '!=', False),
            ('expiry_date', '<=', today),
            ('state', '!=', 'expired'),
        ])
        expired_records.write({
            'state': 'expired'
        })

        in_progress_records = self.search([
            ('expiry_date', '!=', False),
            ('expiry_date', '>', today),
            ('state', '!=', 'in_progress'),
        ])
        in_progress_records.write({
            'state': 'in_progress'
        })


    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.context_today(self)

        for vals in vals_list:
            expiry_date = vals.get('expiry_date')

            if expiry_date:
                expiry_date = fields.Date.to_date(expiry_date)

                vals['state'] = (
                    'expired'
                    if expiry_date <= today
                    else 'in_progress'
                )
            else:
                vals['state'] = 'in_progress'

            if vals.get('employee_ref_id') and 'notify_user_ids' not in vals:
                employee = self.env['hr.employee'].browse(
                    vals['employee_ref_id']
                )

                users = (
                        employee.parent_id.user_id
                        | employee.coach_id.user_id
                        | employee.pro_id.user_id
                )

                if users:
                    vals['notify_user_ids'] = [(6, 0, users.ids)]

        records = super().create(vals_list)

        # Post uploaded files to chatter
        for record in records:
            if record.doc_attachment_ids:
                record._post_new_attachments_to_chatter(
                    record.doc_attachment_ids.ids
                )

        return records


    def write(self, vals):
        # Remember attachments before the write
        old_attachments = {
            record.id: record.doc_attachment_ids.ids
            for record in self
        }

        # ---------------------------------
        # Update state from expiry date
        # ---------------------------------
        if 'expiry_date' in vals:
            today = fields.Date.context_today(self)
            expiry_date = vals.get('expiry_date')

            if expiry_date:
                expiry_date = fields.Date.to_date(expiry_date)

                vals['state'] = (
                    'expired'
                    if expiry_date <= today
                    else 'in_progress'
                )
            else:
                vals['state'] = 'in_progress'

        result = super().write(vals)

        # ---------------------------------
        # Post new attachments to chatter
        # ---------------------------------
        if 'doc_attachment_ids' in vals:
            for record in self:
                old_ids = set(old_attachments.get(record.id, []))
                current_ids = set(record.doc_attachment_ids.ids)

                new_attachment_ids = current_ids - old_ids

                if new_attachment_ids:
                    record._post_new_attachments_to_chatter(
                        list(new_attachment_ids)
                    )

        return result


    @api.constrains('notify_type', 'notify_user_ids')
    def _check_notify_user_ids(self):
        """ Activities need at least one assignee - block saving a
        record configured for Activity/Both without any user selected,
        instead of silently creating zero activities later. """
        for rec in self:
            if rec.notify_type in ('activity', 'both') and \
                    not rec.notify_user_ids:
                raise UserError(_(
                    'Please select at least one user in "Users to '
                    'Notify" when "Notify Via" is set to Activity or '
                    'Both.'))

    def mail_reminder(self):
        """Sending document expiry notification to employees."""
        for record in self.search([('expiry_date', '!=', False)]):
            exp_date = fields.Date.from_string(record.expiry_date)
            days_before = timedelta(days=record.before_days or 0)
            is_expiry_today = fields.Date.today() == exp_date
            is_notification_day = any([record.notification_type == 'single'
                                       and is_expiry_today,
                                       record.notification_type == 'multi'
                                       and (fields.Date.today() == fields.Date.
                                            from_string(
                                           record.expiry_date) - days_before
                                            or is_expiry_today),
                                       record.notification_type == 'everyday'
                                       and fields.Date.today() >= fields.Date.
                                      from_string(
                                           record.expiry_date) - days_before,
                                       record.notification_type ==
                                       'everyday_after'
                                       and fields.Date.today() <=
                                       fields.Date.from_string(
                                           record.expiry_date) + days_before,
                                       not record.notification_type and
                                       fields.Date.today() == fields.Date.
                                      from_string(
                                           record.expiry_date) - timedelta(
                                           days=7), ])
            if is_notification_day:
                if record.notify_type in ('email', 'both'):
                    record._send_expiry_email()
                if record.notify_type in ('activity', 'both'):
                    record._create_expiry_activity()

    def _send_expiry_email(self):
        """Sending document expiry notification email to the employee.
        Unchanged from the original behavior."""
        self.ensure_one()
        employee_name = self.employee_ref_id.name
        document_name = self.name
        expiry_date_str = str(self.expiry_date)
        mail_content = (
            f"Hello {employee_name},<br>Your Document {document_name} "
            f"is going to expire on {expiry_date_str}. "
            "Please renew it before the expiry date."
        )
        subject = _('Document-%s Expired On %s') % (
            document_name, expiry_date_str)
        main_content = {
            'subject': subject,
            'author_id': self.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': self.employee_ref_id.work_email,
        }
        self.env['mail.mail'].create(main_content).send()

    def _create_expiry_activity(self):
        """Creating an Odoo Activity (Discuss/Chatter reminder) for each
        user selected in 'notify_user_ids', instead of (or in addition
        to) sending an email."""
        self.ensure_one()
        if not self.notify_user_ids:
            return
        activity_type = self.env.ref(
            'mail.mail_activity_data_todo', raise_if_not_found=False)
        note = _(
            'Document "%s" for employee %s is going to expire on %s. '
            'Please follow up before the expiry date.'
        ) % (self.name, self.employee_ref_id.name, self.expiry_date)
        for user in self.notify_user_ids:
            self.env['mail.activity'].create({
                'res_model_id': self.env['ir.model']._get_id(self._name),
                'res_id': self.id,
                'activity_type_id': activity_type.id if activity_type
                else False,
                'summary': _('Document expiring: %s') % self.name,
                'note': note,
                'user_id': user.id,
                'date_deadline': self.expiry_date or fields.Date.today(),
            })

    def _post_new_attachments_to_chatter(self, attachment_ids):
        """Post newly uploaded document attachments in the chatter."""
        if not attachment_ids:
            return

        attachments = self.env['ir.attachment'].browse(
            attachment_ids
        ).exists()

        if not attachments:
            return

        file_names = attachments.mapped('name')

        if len(file_names) == 1:
            body = _("Attachment added: %s") % file_names[0]
        else:
            body = _("Attachments added: %s") % ", ".join(file_names)

        self.message_post(
            body=body,
            attachment_ids=attachments.ids,
        )
        


    # @api.constrains('expiry_date')
    # def _check_expiry_date(self):
    #     """This method is called as a constraint whenever the 'expiry_date'
    #      field of an 'hr.employee.document' record is modified."""
    #     for rec in self:
    #         if rec.expiry_date:
    #             exp_date = fields.Date.from_string(rec.expiry_date)
    #             if exp_date < date.today():
    #                 raise UserError(_('Your Document Is Expired.'))
