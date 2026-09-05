from odoo import models, fields, api


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'


    payment_method_id = fields.Many2one(
        comodel_name='account.payment.method.line',
        string="Payment Method",
        compute="_compute_payment_method_id",
        store=True,
        readonly=True,
        check_company=True,
        domain="[('company_id', '=', company_id)]",
    )

    @api.depends(
        'move_line_id.move_id.matched_payment_ids.payment_method_line_id'
    )
    def _compute_payment_method_id(self):
        for line in self:
            payment_method = False

            move = line.move_line_id.move_id if line.move_line_id else False

            if move and move.is_invoice(include_receipts=True):
                payments = move.matched_payment_ids.filtered(
                    lambda p: p.company_id == line.company_id
                )
                if payments:
                    payment_method = payments[:1].payment_method_line_id

            line.payment_method_id = payment_method



    def action_print_analytical_report(self):
        """Called from the list view toolbar — opens the print wizard."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Print Analytical Item Report',
            'res_model': 'analytical.item.print.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_analytic_line_ids': self.ids,
            },
        }