from odoo import models, api, exceptions, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_draft(self):
        # Check if user has Invoicing group but NOT the Manager group
        if self.env.user.has_group('account.group_account_invoice') and not self.env.user.has_group(
                'account.group_account_readonly'):
            raise exceptions.AccessError(_("You are not allowed to reset invoices to draft."))
        return super().button_draft()

    # def button_cancel(self):
    #     # Check if user has Invoicing group but NOT the Manager group
    #     if self.env.user.has_group('account.group_account_invoice') and not self.env.user.has_group(
    #             'account.group_account_readonly'):
    #         raise exceptions.AccessError(_("You are not allowed to cancel invoices."))
    #     return super().button_cancel()


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    #
    # def action_draft(self):
    #     if self.env.user.has_group('account.group_account_invoice') and not self.env.user.has_group(
    #             'account.group_account_readonly'):
    #         raise exceptions.AccessError(_(" You are not allowed to reset payments to draft."))
    #     return super().action_draft()
    #
    # def action_cancel(self):
    #     if self.env.user.has_group('account.group_account_invoice') and not self.env.user.has_group(
    #             'account.group_account_readonly'):
    #         raise exceptions.AccessError(_(" You are not allowed to cancel payment."))
    #     return super().action_cancel()

    @api.model
    def default_get(self, fields_list):
        """
        Override default_get to prioritize the journal set on the user profile.
        """
        res = super(AccountPayment, self).default_get(fields_list)

        # Only override if journal_id is being requested and hasn't been set by context
        if 'journal_id' in fields_list:
            user_default_journal = self.env.user.default_payment_journal_id
            if user_default_journal:
                res['journal_id'] = user_default_journal.id

        return res


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields_list):
        """
        Override default_get to prioritize the journal set on the user profile.
        """
        res = super(AccountPaymentRegister, self).default_get(fields_list)

        # Only override if journal_id is being requested and hasn't been set by context
        if 'journal_id' in fields_list:
            user_default_journal = self.env.user.default_payment_journal_id
            if user_default_journal:
                res['journal_id'] = user_default_journal.id

        return res
