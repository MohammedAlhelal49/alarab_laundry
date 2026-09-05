
from odoo import models, fields, api
from odoo.exceptions import UserError



class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    payment_order = fields.Integer(
        string='Payment Order'
    )

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)

        vals['payment_order'] = self.payment_order

        return vals


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')

    payment_order = fields.Integer(
        string='Payment Order'
    )

    def action_post(self):
        res = super().action_post()

        for payment in self:
            if payment.sale_order_id:
                sale_order = payment.sale_order_id

                # Link the payment to the sale order
                sale_order.payment_id = payment

                # If no invoice yet, create it
                if not sale_order.invoice_ids:
                    invoice_wizard = payment.env['sale.advance.payment.inv'].with_context(
                        active_ids=[sale_order.id],
                        active_id=sale_order.id
                    ).create({
                        'advance_payment_method': 'delivered',
                    })
                    invoice_wizard.create_invoices()

                # Post the invoice if it's still in draft
                invoice = sale_order.invoice_ids.filtered(lambda inv: inv.state == 'draft')
                if invoice:
                    invoice.action_post()
                # ✅ Set memo from the invoice name
                if sale_order.invoice_ids:
                    payment.memo = sale_order.invoice_ids[0].name
                # Reconcile the payment with the invoice
                posted_invoice = sale_order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
                if posted_invoice:
                    for inv in posted_invoice:
                        lines_to_reconcile = (payment.move_id.line_ids + inv.line_ids).filtered(
                            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                        )
                        if lines_to_reconcile:
                            lines_to_reconcile.reconcile()

                            payment.state = 'paid'

        return res
