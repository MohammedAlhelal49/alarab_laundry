# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, _


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def _do_reverse_moves(self):
        self.unlink_journals()

    def unlink(self):
        self.unlink_journals()
        return super().unlink()

    def unlink_journals(self):
        for rec in self:
            move_ids = rec.account_move_ids
            print(move_ids)

            payment_ids = move_ids.mapped('payment_ids')
            matched_payment_ids = move_ids.mapped('matched_payment_ids')

            all_payments = payment_ids | matched_payment_ids

            # -------------------------
            # HANDLE PAYMENTS
            # -------------------------
            if all_payments:

                draft_payments = all_payments.filtered(lambda p: p.state == 'draft')
                posted_payments = all_payments.filtered(
                    lambda p: p.state in ('paid', 'in_progress', 'canceled', 'rejected'))

                # cancel posted payments first
                if posted_payments:
                    posted_payments.action_cancel()

                # now delete all
                (draft_payments | posted_payments).unlink()

            # -------------------------
            # HANDLE JOURNAL ENTRIES
            # -------------------------

            move_ids = rec.account_move_ids
            if move_ids:
                draft_moves = move_ids.filtered(lambda m: m.state == 'draft')
                posted_moves = move_ids.filtered(lambda m: m.state == 'posted')

                # cancel posted moves
                if posted_moves:
                    posted_moves.button_cancel()

                # delete all moves
                (draft_moves | posted_moves).unlink()

    def unlink_all_journals(self):
        orphaned_moves = self.env['account.move'].search(
            [('expense_sheet_id', '=', False), ('line_ids.expense_id', '!=', False)])

        orphaned_payments = orphaned_moves.mapped('payment_ids') | orphaned_moves.mapped('matched_payment_ids')

        print(orphaned_moves)

        print(orphaned_payments)

        if orphaned_payments:
            draft_payments = orphaned_payments.filtered(lambda p: p.state == 'draft')
            posted_payments = orphaned_payments.filtered(
                lambda p: p.state != 'draft')

            # cancel posted payments first
            if posted_payments:
                posted_payments.action_cancel()

            # now delete all
            (draft_payments | posted_payments).unlink()

        # -------------------------
        # HANDLE JOURNAL ENTRIES
        # -------------------------
        if orphaned_moves:
            draft_moves = orphaned_moves.filtered(lambda m: m.state == 'draft')
            posted_moves = orphaned_moves.filtered(lambda m: m.state == 'posted')

            # cancel posted moves
            if posted_moves:
                posted_moves.button_cancel()

            # delete all moves
            (draft_moves | posted_moves).unlink()
