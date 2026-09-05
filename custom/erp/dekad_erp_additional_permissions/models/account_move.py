from odoo import models, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # =====================================================
    # POST / CONFIRM PAYMENT
    # =====================================================

    def action_post(self):

        # Prevent recursion
        if self.env.context.get('skip_payment_permission'):
            return super().action_post()

        if not self.env.user.has_group(
            'dekad_erp_additional_permissions.group_account_payment_confirm'
        ):
            raise ValidationError(
                _("You do not have permission to confirm payments.")
            )

        return super(
            AccountPayment,
            self.with_context(
                skip_payment_permission=True,
                skip_account_move_permission=True,
            )
        ).action_post()

    # =====================================================
    # CANCEL PAYMENT
    # =====================================================

    def action_cancel(self):

        if self.env.context.get('skip_payment_permission'):
            return super().action_cancel()

        if not self.env.user.has_group(
            'dekad_erp_additional_permissions.group_account_payment_cancel'
        ):
            raise ValidationError(
                _("You do not have permission to cancel payments.")
            )

        return super(
            AccountPayment,
            self.with_context(
                skip_payment_permission=True,
                skip_account_move_permission=True,
            )
        ).action_cancel()

    # =====================================================
    # RESET TO DRAFT
    # =====================================================

    def action_draft(self):

        if self.env.context.get('skip_payment_permission'):
            return super().action_draft()

        if not self.env.user.has_group(
            'dekad_erp_additional_permissions.group_account_payment_draft'
        ):
            raise ValidationError(
                _("You do not have permission to reset payments to draft.")
            )

        return super(
            AccountPayment,
            self.with_context(
                skip_payment_permission=True,
                skip_account_move_permission=True,
            )
        ).action_draft()

    # =====================================================
    # DELETE
    # =====================================================

    def unlink(self):

        if self.env.context.get('skip_payment_permission'):
            return super().unlink()

        if not self.env.user.has_group(
            'dekad_erp_additional_permissions.group_account_payment_delete'
        ):
            raise ValidationError(
                _("You do not have permission to delete payments.")
            )

        return super(
            AccountPayment,
            self.with_context(
                skip_payment_permission=True,
                skip_account_move_permission=True,
            )
        ).unlink()

class AccountMove(models.Model):
    _inherit = 'account.move'

    # =====================================================
    # POST
    # =====================================================

    def action_post(self):

        # Skip internal payment operations
        if self.env.context.get('skip_account_move_permission'):
            return super().action_post()

        if not self.env.user.has_group(
            'dekad_erp_additional_permissions.group_account_move_post'
        ):
            raise ValidationError(
                _("You do not have permission to post accounting entries.")
            )

        return super().action_post()

    # =====================================================
    # CANCEL
    # =====================================================

    def button_cancel(self):

        # Skip internal payment operations
        if self.env.context.get('skip_account_move_permission'):
            return super().button_cancel()

        if not self.env.user.has_group(
            'dekad_erp_additional_permissions.group_account_move_cancel'
        ):
            raise ValidationError(
                _("You do not have permission to cancel accounting entries.")
            )

        return super().button_cancel()

    # =====================================================
    # RESET TO DRAFT
    # =====================================================

    def button_draft(self):

        # Skip internal payment operations
        if self.env.context.get('skip_account_move_permission'):
            return super().button_draft()

        if not self.env.user.has_group(
            'dekad_erp_additional_permissions.group_account_move_reset_to_draft'
        ):
            raise ValidationError(
                _("You do not have permission to reset entries to draft.")
            )

        return super().button_draft()

    # =====================================================
    # DELETE
    # =====================================================

    def unlink(self):

        # Skip internal payment operations
        if self.env.context.get('skip_account_move_permission'):
            return super().unlink()

        if not self.env.user.has_group(
            'dekad_erp_additional_permissions.group_account_move_delete'
        ):
            raise ValidationError(
                _("You do not have permission to delete accounting entries.")
            )

        return super().unlink()