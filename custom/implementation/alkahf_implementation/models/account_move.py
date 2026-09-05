from odoo import models, fields, api, _
import re
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    has_discount_line = fields.Boolean(compute='_compute_discount_info', store=False)
    discount_line_name = fields.Char(compute='_compute_discount_info', store=False)
    discount_line_percent = fields.Char(compute='_compute_discount_info', store=False)
    discount_line_amount = fields.Monetary(
        compute='_compute_discount_info',
        store=False,
        currency_field='currency_id'
    )


    @api.depends('invoice_line_ids')
    def _compute_discount_info(self):
        percent_regex = re.compile(r'(\d+(?:\.\d+)?)\s*%')

        for move in self:
            discount_lines = move.invoice_line_ids.filtered(
                lambda l: l.product_id and l.product_id.is_discount
            )

            if discount_lines:
                move.has_discount_line = True
                move.discount_line_name = "Discount"

                # Sum the percentages parsed from line.name like "Discount 5.00%"
                total_percent = 0.0
                for line in discount_lines:
                    match = percent_regex.search(line.name or "")
                    if match:
                        try:
                            total_percent += float(match.group(1))
                        except ValueError:
                            pass

                move.discount_line_percent = f"{total_percent:.2f}" if total_percent else ""

                # Always store discount amount as POSITIVE value
                move.discount_line_amount = abs(
                    sum(line.price_subtotal for line in discount_lines)
                )

            else:
                move.has_discount_line = False
                move.discount_line_name = ''
                move.discount_line_percent = ''
                move.discount_line_amount = 0.0


    sale_order_id = fields.Many2one(
            'sale.order',
            compute='_compute_sale_order_id',
            store=True
        )

    serial_number = fields.Char(
        string='Serial Number',
        copy=False,
        readonly=True,
        index=True,
    )

    def action_post(self):
        res = super().action_post()

        for move in self:
            if not move.serial_number:
                move.serial_number = move._generate_serial_number()

        return res

    def _generate_serial_number(self):
        self.ensure_one()

        prefix = self.company_id.move_serial_prefix or 'JV'

        moves = self.search([
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'posted'),
            ('serial_number', '!=', False),
        ])

        max_number = 0

        for move in moves:
            try:
                num = int(move.serial_number.split('/')[-1])
                if num > max_number:
                    max_number = num
            except Exception:
                continue

        next_number = max_number + 1

        return f"{prefix}/{str(next_number).zfill(6)}"


    @api.depends('invoice_line_ids.sale_line_ids.order_id')
    def _compute_sale_order_id(self):
        for move in self:
            sale = move.invoice_line_ids.mapped('sale_line_ids.order_id')
            move.sale_order_id = sale[:1] if sale else False

    def get_rent_receipt_payments(self):
        self.ensure_one()

        result = []

        # Regular Payments
        for pay in self.matched_payment_ids:
            result.append({
                'type': 'payment',
                'payment_order': pay.payment_order or 999999,
                'is_warranty': False,

                'name': pay.memo if hasattr(pay, 'memo') else '',
                'amount': pay.amount,
                'currency': pay.currency_id.name,
                'check_number': self.name or '',
                'partner_bank_id': pay.partner_bank_id.acc_number or '',
                'date': pay.date,
                'bank': '',
            })

        # PDC Payments
        for pdc in self.pdc_payment_ids.filtered(
                lambda p:
                p.state in ('deposited', 'done')
                or (
                        p.state == 'registered'
                        and p.is_warranty_cheque
                )
        ):
            result.append({
                'type': 'pdc',
                'payment_order': pdc.payment_order or 999999,
                'is_warranty': pdc.is_warranty_cheque,

                'name': pdc.memo or '',
                'amount': pdc.payment_amount,
                'currency': pdc.currency_id.name,
                'check_number': pdc.reference or '',
                'partner_bank_id': '',
                'date': pdc.due_date,
                'bank': pdc.bank_id.name or '',
            })

        return sorted(
            result,
            key=lambda x: (
                x['is_warranty'],
                x['payment_order']
            )
        )

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref('alkahf_implementation.action_report_trading_tax_invoice').report_action(self.id)

