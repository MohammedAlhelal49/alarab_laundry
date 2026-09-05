from odoo import models

INCOME_TYPES = {'income', 'income_other'}


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self, is_modify=False):
        res = super().reverse_moves(is_modify=is_modify)

        refund_account = self.env.company.refund_income_account_id
        if not refund_account:
            return res

        for move in self.new_move_ids:
            if move.move_type != 'out_refund':
                continue
            lines_to_update = move.line_ids.filtered(
                lambda l: l.account_id.account_type in INCOME_TYPES
            )
            if lines_to_update:
                lines_to_update.write({'account_id': refund_account.id})

        return res
