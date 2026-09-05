from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    auto_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
    )

    @api.onchange("auto_account_id")
    def _onchange_auto_account_id(self):
        for move in self:
            distribution = {}

            if move.auto_account_id:
                distribution = {
                    str(move.auto_account_id.id): 100,
                }

            for line in move.invoice_line_ids:
                line.analytic_distribution = distribution

            if move.journal_id.apply_receivable_analytic:
                move.line_ids.filtered(
                    lambda l: l.display_type == "payment_term"
                ).analytic_distribution = distribution


    @api.depends(
        "invoice_payment_term_id",
        "invoice_date",
        "currency_id",
        "amount_total_in_currency_signed",
        "invoice_date_due",
        "auto_account_id",
    )
    def _compute_needed_terms(self):
        super()._compute_needed_terms()

        for invoice in self.filtered(lambda m: m.is_invoice(True)):
            if not invoice.journal_id.apply_receivable_analytic:
                continue

            if not invoice.auto_account_id:
                continue

            analytic_distribution = {
                str(invoice.auto_account_id.id): 100,
            }

            needed_terms = {}

            for key, values in (invoice.needed_terms or {}).items():
                vals = dict(values)
                vals["analytic_distribution"] = analytic_distribution
                needed_terms[key] = vals

            invoice.needed_terms = needed_terms



class AccountJournal(models.Model):
    _inherit = "account.journal"

    apply_receivable_analytic = fields.Boolean(
        string="Apply Analytic on Receivable Line",
        help="Copy the invoice analytic account to the Accounts Receivable journal item.",
    )