# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

CASH_CONTROL_BYPASS_GROUP = 'dekad_pos_sale_enhancement.group_pos_cash_control_bypass'


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _notify_employees_cash_difference(self):
        """
        Send notification to selected employees when cash difference is detected.
        Sends both email and creates activity for follow-up.
        """
        self.ensure_one()

        # Get selected employees from POS config
        employees_to_notify = self.config_id.cash_difference_notify_employee_ids

        if not employees_to_notify:
            _logger.warning(
                f'No employees configured to receive notifications for POS {self.config_id.name}. '
                f'Please configure employees in POS settings.'
            )
            return

        # Get mail template
        template = self.env.ref(
            'pos_cash_difference_notification.mail_template_cash_difference',
            raise_if_not_found=False
        )

        # Determine difference type
        cash_difference = self.cash_register_difference
        difference_type = _('Shortage') if cash_difference < 0 else _('Overage')

        for employee in employees_to_notify:
            # Get employee's email (work_email or user's email)
            email = employee.work_email or (employee.user_id and employee.user_id.email)

            # Send email notification
            if template and email:
                try:
                    template.with_context(
                        employee_name=employee.name,
                        difference_type=difference_type,
                    ).send_mail(self.id, force_send=True, email_values={
                        'email_to': email,
                    })
                    _logger.info(
                        f'Cash difference notification email sent to {employee.name} '
                        f'for session {self.name}'
                    )
                except Exception as e:
                    _logger.error(f'Failed to send email to {employee.name}: {str(e)}')
            elif not email:
                _logger.warning(f'Employee {employee.name} has no email configured.')

            # Create activity (To-Do) for the employee's user (if linked)
            if employee.user_id:
                try:
                    self.env['mail.activity'].create({
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'summary': _('Cash Difference Alert: %s') % self.name,
                        'note': self._prepare_activity_note(difference_type),
                        'user_id': employee.user_id.id,
                        'res_id': self.id,
                        'res_model_id': self.env['ir.model']._get('pos.session').id,
                        'date_deadline': fields.Date.today(),
                    })
                    _logger.info(
                        f'Cash difference activity created for {employee.name} '
                        f'for session {self.name}'
                    )
                except Exception as e:
                    _logger.error(f'Failed to create activity for {employee.name}: {str(e)}')
            else:
                _logger.warning(
                    f'Employee {employee.name} has no linked user. Activity not created.'
                )

    def _prepare_activity_note(self, difference_type):
        """Prepare the activity note with all relevant information."""
        currency = self.currency_id or self.company_id.currency_id

        note = _("""
            <p><strong>⚠️ Cash Difference Detected</strong></p>
            <ul>
                <li><strong>Session:</strong> %(session)s</li>
                <li><strong>Point of Sale:</strong> %(pos)s</li>
                <li><strong>Cashier:</strong> %(cashier)s</li>
                <li><strong>Date/Time:</strong> %(datetime)s</li>
                <li><strong>Expected Amount:</strong> %(expected)s</li>
                <li><strong>Actual Amount:</strong> %(actual)s</li>
                <li><strong>Difference:</strong> <span style="color: red;">%(difference)s (%(type)s)</span></li>
            </ul>
        """) % {
            'session': self.name,
            'pos': self.config_id.name,
            'cashier': self.user_id.name,
            'datetime': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'expected': self._format_currency(self.cash_register_balance_end, currency),
            'actual': self._format_currency(self.cash_register_balance_end_real, currency),
            'difference': self._format_currency(abs(self.cash_register_difference), currency),
            'type': difference_type,
        }
        return note

    def _format_currency(self, amount, currency):
        """Format amount with currency symbol."""
        return f"{currency.symbol} {amount:,.2f}"

    def _should_notify_cash_difference(self):
        """
        Check if notification should be sent based on configuration.
        """
        self.ensure_one()

        config = self.config_id

        # Check if notifications are enabled
        if not config.notify_on_cash_difference:
            return False

        # Check if employees are configured
        if not config.cash_difference_notify_employee_ids:
            return False

        # Check if difference exceeds threshold
        threshold = config.cash_difference_threshold or 0.0
        cash_difference = abs(self.cash_register_difference or 0.0)

        return cash_difference >= threshold

    def action_pos_session_close(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """
        Override the session close action to send notifications.
        """
        # Call the original method first
        result = super().action_pos_session_close(
            balancing_account=balancing_account,
            amount_to_balance=amount_to_balance,
            bank_payment_method_diffs=bank_payment_method_diffs
        )

        # Check and send notifications for each session
        for session in self:
            if session._should_notify_cash_difference():
                session._notify_employees_cash_difference()
                _logger.info(
                    f'Cash difference notification triggered for session {session.name}. '
                    f'Difference: {session.cash_register_difference}'
                )

        return result

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data += ['product.multi.uom.price']
        return data

    def _load_pos_data(self, data):
        """Inject per-user cash control bypass flag into session data,
        following the same pattern as _has_cash_move_perm in Odoo 18 core.
        """
        result = super()._load_pos_data(data)
        result['data'][0]['_cash_control_bypass'] = self.env.user.has_group(
            CASH_CONTROL_BYPASS_GROUP
        )
        return result
