from odoo import api, fields, models, _
from pytz import timezone
from datetime import datetime


class PurchaseOrderInherited(models.Model):
    _inherit = "purchase.order"


    def action_open_discount_wizard(self):
        """Open the Purchase Discount wizard as a dialog popup.

        Mirrors sale.order.action_open_discount_wizard().
        The active_id context key is picked up by the wizard's default
        lambda to auto-populate purchase_order_id.
        """
        self.ensure_one()
        return {
            'name': _("Discount"),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.discount',
            'view_mode': 'form',
            'target': 'new',
            # active_id is used by the wizard's Many2one default
            'context': {'active_id': self.id},
        }



    def button_confirm(self):
        res = super().button_confirm()

        company = self.env.company

        for order in self:
            receipt_bill_policy = order.order_line.filtered(
                lambda rec: rec.product_id.purchase_method == 'receive'
            )

            if (
                    receipt_bill_policy
                    and company.direct_purchase_receipt_invoice
                    and company.direct_purchase_receipt_delivery_state == 'draft'
            ):
                order.message_post(
                    body=(
                        "Direct purchase receipt/invoice was skipped because "
                        "one or more products use a bill policy based on received quantities."
                    ),
                    subtype_xmlid="mail.mt_note",
                )
                continue

            if company.direct_purchase_receipt_invoice:
                if company.direct_purchase_receipt_delivery_state == 'validated':
                    deliveries = order.picking_ids
                    deliveries.button_validate()

                invoices = order.action_create_invoice()
                if order.invoice_ids and company.direct_purchase_receipt_invoice_state == 'posted':
                    order.invoice_ids.write({
                        "invoice_date": datetime.now().astimezone(
                            timezone("Asia/Dubai")
                        )
                    })
                    order.invoice_ids.action_post()

        return res


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    amount_received = fields.Float(
        string='Amount received', digits='Amount received',
        compute="_compute_amount_received", readonly=True, store=True)

    amount_to_invoice = fields.Float(compute='_compute_amount_to_invoice', string='Amount to bill', store=True,
                                     readonly=True,
                                     digits='Amount to invoice')

    amount_invoiced = fields.Float(compute='_compute_amount_invoiced', string='Amount Billed', store=True,
                                   readonly=True,
                                   digits='Amount Invoiced')

    price_unit_vat = fields.Monetary(
        string="Unit Price (incl. VAT)",
        compute="_compute_price_unit_vat",
        store=True,
        currency_field="currency_id",
        help="Unit price including VAT. Editing this field updates the Unit Price (excl. VAT).",
    )

    line_index = fields.Integer(string='Line #', compute='_compute_line_index', store=False)

    @api.depends('order_id.order_line')
    def _compute_line_index(self):
        for order in self.mapped('order_id'):
            for idx, line in enumerate(order.order_line.sorted('sequence'), start=1):
                line.line_index = idx

    # ------------------------------
    # Compute VAT-inclusive unit price
    # ------------------------------
    @api.depends("price_unit", "taxes_id")
    def _compute_price_unit_vat(self):
        for line in self:
            price_ex = line.price_unit or 0.0

            if not line.taxes_id:
                line.price_unit_vat = price_ex
                continue

            taxes = line.taxes_id.compute_all(
                price_ex,
                currency=line.order_id.currency_id,
                quantity=1,
                product=line.product_id,
                partner=line.order_id.partner_id,
            )

            line.price_unit_vat = taxes["total_included"]

    # ------------------------------
    # Onchange
    # ------------------------------
    @api.onchange("price_unit_vat", "taxes_id")
    def _onchange_price_unit_vat(self):
        for line in self:
            values = set(line.taxes_id.mapped('price_include_override'))
            tax_type = False
            has_included = 'tax_included' in values
            has_excluded = False in values or 'tax_excluded' in values

            if has_included and has_excluded:
                tax_type = "mix"
            elif has_included:
                tax_type = "tax_included"
            else:
                tax_type = "tax_excluded"
            print(tax_type)

            if not line.price_unit_vat:
                line.price_unit = 0.0
                continue

            if not line.taxes_id:
                line.price_unit = line.price_unit_vat
                continue

            currency = line.order_id.currency_id

            # Use tax engine in reverse mode
            taxes = line.taxes_id.with_context(force_price_include=True).compute_all(
                line.price_unit_vat,
                currency=currency,
                quantity=1,
                product=line.product_id,
                partner=line.order_id.partner_id,
            )

            if tax_type == "mix":
                line.price_unit_vat = line.price_unit

                return {
                    'warning': {
                        'title': _('Mixed Taxes Detected'),
                        'message': _(
                            'Since You are using both Included and Excluded taxes on the same line.\n'
                            'You can only input the price from the price unit field'
                        )
                    }
                }

            price_ex = taxes["total_excluded"]
            price_in = taxes["total_included"]

            line.price_unit = currency.round(price_in if tax_type == "tax_included" else price_ex)

    @api.depends('qty_received', 'price_unit')
    def _compute_amount_received(self):
        for rec in self:
            rec.amount_received = rec.qty_received * rec.price_unit

    @api.depends('qty_to_invoice', 'price_unit')
    def _compute_amount_to_invoice(self):
        for rec in self:
            rec.amount_to_invoice = rec.qty_to_invoice * rec.price_unit

    @api.depends('qty_invoiced', 'price_unit')
    def _compute_amount_invoiced(self):
        for rec in self:
            rec.amount_invoiced = rec.qty_invoiced * rec.price_unit