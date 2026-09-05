# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    auto_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
    )

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        vals_list = super()._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
        )

        if self.auto_account_id:

            analytic_distribution = {
                str(self.auto_account_id.id): 100,
            }

            for vals in vals_list:

                # Receive Money -> apply on Debit line only
                if (
                    self.payment_type == 'inbound'
                    and vals.get('debit', 0) > 0
                ):
                    vals['analytic_distribution'] = analytic_distribution

                # Send Money -> apply on Credit line only
                elif (
                    self.payment_type == 'outbound'
                    and vals.get('credit', 0) > 0
                ):
                    vals['analytic_distribution'] = analytic_distribution

        return vals_list