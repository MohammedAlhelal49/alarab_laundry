from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string='Payment Method',
        compute='_compute_payment_method',
        store=True
    )

    @api.depends('move_id')
    def _compute_payment_method(self):
        for line in self:
            payment_method = False

            # check if move is invoice
            move = line.move_id

            if move.move_type in ('out_invoice', 'in_invoice'):
                payments = move._get_reconciled_payments()

                if payments:
                    payment_method = payments[0].payment_method_line_id

            line.payment_method_line_id = payment_method

    @api.onchange("product_id")
    def _onchange_product_id_default_analytic(self):
        for line in self:
            if (
                line.display_type == "product"
                and line.move_id.auto_account_id
                and not line.analytic_distribution
            ):
                line.analytic_distribution = {
                    str(line.move_id.auto_account_id.id): 100,
                }