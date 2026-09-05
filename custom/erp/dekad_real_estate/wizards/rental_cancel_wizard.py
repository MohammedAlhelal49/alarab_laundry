from odoo import models, api, _, fields
from odoo.exceptions import UserError
from datetime import date


class RentalCancelWizard(models.TransientModel):
    _name = 'rental.cancel.wizard'
    _description = 'Rental Cancel Wizard'

    reason = fields.Text(string="Cancellation Reason")
    checkout_date = fields.Date(string="Early Checkout Date")

    show_checkout_date = fields.Boolean(
        string="Show Checkout Date", compute="_compute_show_checkout_date", store=False
    )

    @api.depends_context()
    def _compute_show_checkout_date(self):
        for wizard in self:
            wizard.show_checkout_date = self.env.context.get('cancel_type') == 'early_checkout'

    def _check_invoice_required_when_paid(self, sale_order, action_label):
        invoices = sale_order.invoice_ids.filtered(lambda inv: inv.state != 'cancel')

        if not invoices:
            raise UserError(_(
                "You cannot use %s because there is no invoice for this order."
            ) % action_label)

        # Allow paid OR partially paid
        if sale_order.rent_state not in ['paid', 'partially_paid']:
            raise UserError(_(
                "You cannot use %s because the order is not paid or partially paid."
            ) % action_label)


    def _get_sale_order(self):
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        if not sale_order:
            raise UserError(_("No Sale Order found in context."))
        return sale_order

    def action_cancel_paid(self):
        sale_order = self._get_sale_order()
        self._check_invoice_required_when_paid(sale_order, _("Cancel & Refund"))

        invoices = sale_order.invoice_ids.filtered(lambda inv: inv.state != 'cancel')
        for invoice in invoices:
            for line in invoice.line_ids:
                if line.reconciled:
                    line.remove_move_reconcile()

            related_payments = self.env['account.payment'].search([
                ('memo', '=', invoice.name)
            ])
            for payment in related_payments:
                if payment.state == 'posted':
                    payment.action_draft()
                if payment.state in ('draft', 'in_process'):
                    payment.action_cancel()

                payment.message_post(body=_("Payment %s cancelled because it was linked to invoice %s.") % (
                    payment.name, invoice.name))

            if invoice.state == 'posted':
                invoice.button_draft()
            invoice.button_cancel()
            invoice.message_post(body=_("%s cancelled as Cancel & Refund.Invoice and related payment(s) reversed.") % invoice.name)

        for picking in sale_order.picking_ids.filtered(lambda p: p.state in ('done', 'assigned', 'confirmed')):
            picking.action_cancel()

        sale_order._action_cancel()
        sale_order.write({
            'cancel_type': 'paid_cancel',
            'cancel_reason': self.reason,
        })
        sale_order.message_post(body=_("Order %s cancelled as Cancel & Refund.Invoice and related payment(s) reversed.") % sale_order.name)
        return {'type': 'ir.actions.act_window_close'}

    def action_no_show_cancel(self):
        sale_order = self._get_sale_order()
        self._check_invoice_required_when_paid(sale_order, _("Cancel without Refund"))

        sale_order._action_cancel()
        sale_order.write({
            'cancel_type': 'no_show',
            'cancel_reason': self.reason,
        })
        sale_order.message_post(body=_("%s cancelled as Cancel without Refund.") % sale_order.name)
        return {'type': 'ir.actions.act_window_close'}

    def action_free_cancel(self):
        sale_order = self._get_sale_order()

        sale_order._action_cancel()
        sale_order.write({
            'cancel_type': 'free_cancel',
            'cancel_reason': self.reason,
        })
        sale_order.message_post(body=_("%s cancelled as No Response.") % sale_order.name)
        return {'type': 'ir.actions.act_window_close'}

    def open_checkout_date_wizard(self):
        # Create a fresh wizard record with same reason passed
        sale_order = self._get_sale_order()

        self._check_invoice_required_when_paid(
            sale_order, _("Early Checkout")
        )
        new_wizard = self.create({
            'reason': self.reason,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Early Checkout'),
            'res_model': 'rental.cancel.wizard',
            'view_mode': 'form',
            'res_id': new_wizard.id,
            'target': 'new',
            'context': dict(self.env.context, cancel_type='early_checkout'),
        }

    def action_early_checkout(self):
        sale_order = self._get_sale_order()

        # Validation: require date
        if not self.checkout_date:
            raise UserError(_("You must choose the Early Checkout date."))

        today = date.today()

        if self.checkout_date < today:
            raise UserError(_(
                "Early Checkout date cannot be earlier than today's date (%s)."
            ) % today)

        if not (sale_order.rent_start_date <= self.checkout_date <= sale_order.rent_end_date):
            raise UserError(_(
                "Checkout date must be between rental start date (%s) and rental end date (%s)."
            ) % (sale_order.rent_start_date, sale_order.rent_end_date))

        self._check_invoice_required_when_paid(sale_order, _("Early Checkout"))

        sale_order._action_cancel()
        sale_order.write({
            'cancel_type': 'early_checkout',
            'cancel_reason': self.reason,
            'checkout_date': self.checkout_date,

        })
        sale_order.message_post(body=_("%s cancelled as Early Checkout.") % sale_order.name)
        return {'type': 'ir.actions.act_window_close'}
