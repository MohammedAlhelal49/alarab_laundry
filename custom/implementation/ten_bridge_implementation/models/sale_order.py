from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    other_charge_ids = fields.One2many(
        "sale.order.other.charge",
        "sale_order_id",
        string="Other Charges",
        copy=True,
    )

    previous_contract_name = fields.Char(
        string="Previous Contract",
        compute="_compute_previous_contract_name",
        store=False,
    )

    pdc_ids = fields.Many2many(
        'pdc.wizard',
        'sale_order_pdc_wizard_rel',  # explicit relation table name
        'order_id',
        'pdc_id',
        string="Guarantee Cheques",
        domain="[('is_warranty_cheque', '=', True)]",
    )


    @api.depends('partner_id', 'account_analytic_account_id')
    def _compute_previous_contract_name(self):
        for order in self:
            order.previous_contract_name = False

            if not order.partner_id or not order.account_analytic_account_id:
                continue

            previous_order = self.search(
                [
                    ('id', '!=', order.id),
                    ('state', 'in', ('sale', 'done')),
                    ('partner_id', '=', order.partner_id.id),
                    ('account_analytic_account_id', '=', order.account_analytic_account_id.id),
                ],
                order='create_date desc, id desc',
                limit=1,
            )

            order.previous_contract_name = previous_order.name if previous_order else False


    @staticmethod
    def _tb_ar_unit(count, singular, dual, plural):
        """Arabic noun-number agreement: 1 -> singular, 2 -> dual,
        3-10 -> number + plural, 11+ -> number + singular."""
        if count == 1:
            return singular
        if count == 2:
            return dual
        if 3 <= count <= 10:
            return f'{count} {plural}'
        return f'{count} {singular}'

    def get_tb_rental_duration_label(self):
        """Arabic contract-duration label computed from the difference
        between rent_start_date and rent_end_date (e.g. سنة, سنتين,
        ٣ سنين, 11 سنة, with months/days appended when not an exact
        number of years).
        """
        self.ensure_one()
        if not self.rent_start_date or not self.rent_end_date:
            return ''

        delta = relativedelta(self.rent_end_date, self.rent_start_date)
        years, months, days = delta.years, delta.months, delta.days

        # An inclusive end date (e.g. yearly contracts end one day before
        # the anniversary) still counts as a full extra unit.
        if days >= 28:
            months += 1
            days = 0
        if months >= 12:
            years += 1
            months = 0

        parts = []
        if years:
            parts.append(self._tb_ar_unit(years, 'سنة', 'سنتين', 'سنين'))
        if months:
            parts.append(self._tb_ar_unit(months, 'شهر', 'شهرين', 'أشهر'))
        if days:
            parts.append(self._tb_ar_unit(days, 'يوم', 'يومين', 'أيام'))

        return ' و'.join(parts) if parts else 'أقل من يوم'

    def _tb_aggregate_payments(self, include_warranty=False):
        seen = set()
        result = []
        posted_invoices = self.invoice_ids.filtered(
            lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
        )
        for invoice in posted_invoices:
            for pay in invoice.tb_get_rent_payments(include_warranty=include_warranty):
                key = (pay.get('type'), pay.get('check_number'), pay.get('amount'))
                if key in seen:
                    continue
                seen.add(key)
                result.append(pay)
        result.sort(key=lambda x: (x.get('payment_order', 999999),))
        return result

    def get_tb_rent_payment_lines(self):
        """Regular payments + non-warranty PDCs (rent table)."""
        self.ensure_one()
        return self._tb_aggregate_payments(include_warranty=False)

    def get_tb_warranty_payment_lines(self):
        """Warranty PDCs only (التأمينات table), sourced directly from the
        Guarantee Cheques tab (pdc_ids) instead of invoice payment history.
        """
        self.ensure_one()
        warranty_pdcs = self.pdc_ids.filtered(lambda p: p.is_warranty_cheque)
        result = []
        for pdc in warranty_pdcs:
            result.append({
                'amount': pdc.payment_amount,
                'currency': pdc.currency_id.name or '',
                'check_number': pdc.reference or '',
                'bank': pdc.bank_id.name or '',
                'name': pdc.memo or (pdc.partner_id.name or ''),
            })
        return result


    def get_tb_amount_in_words(self):
        """Spelled-out rental amount, reusing Odoo's standard
        res.currency.amount_to_text() helper (same one used on invoices).
        """
        self.ensure_one()
        if not self.amount_total:
            return ''
        return self.currency_id.amount_to_text(self.amount_total)

    def get_tb_discount_amount_in_words(self):
        """Spelled-out discount amount."""
        self.ensure_one()
        if not self.discount_total:
            return ''
        return self.currency_id.amount_to_text(self.discount_total)


    def action_tb_print_rental_summary(self):
        self.ensure_one()
        return self.env.ref(
            'ten_bridge_implementation.action_report_tb_rental_contract_summary'
        ).report_action(self.id)

    @staticmethod
    def _extract_sequence(name):
        if name and " - " in name:
            return name.split(" - ", 1)[1]
        return name

    @api.model
    def create(self, vals):
        order = super().create(vals)

        if order.name:
            sequence = self._extract_sequence(order.name)
            if sequence != order.name:
                order.with_context(skip_name_cleanup=True).write({
                    "name": sequence
                })

        return order

    def write(self, vals):
        res = super().write(vals)

        if self.env.context.get("skip_name_cleanup"):
            return res

        for order in self:
            if order.name:
                sequence = self._extract_sequence(order.name)
                if sequence != order.name:
                    order.with_context(skip_name_cleanup=True).write({
                        "name": sequence
                    })

        return res

    discount_total = fields.Monetary(
        string="Discount Total",
        compute="_compute_discount_total",
        currency_field="currency_id",
    )

    @api.depends(
        "order_line.price_total",
        "order_line.product_id",
        "order_line.product_id.product_tmpl_id.is_discount",
    )
    def _compute_discount_total(self):
        for order in self:
            order.discount_total = sum(
                line.price_total
                for line in order.order_line
                if line.product_id.product_tmpl_id.is_discount
            )


