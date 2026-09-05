from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def tb_get_rent_payments(self, include_warranty=False):
        """Return payment dicts for this invoice.
        include_warranty=False  → regular payments + non-warranty PDCs (rent table)
        include_warranty=True   → warranty PDCs only (insurance table)
        """
        self.ensure_one()
        result = []

        if not include_warranty:
            # ── Regular reconciled payments ──────────────────────────────
            reconciled_payments = (
                self.line_ids.mapped('matched_debit_ids.debit_move_id.payment_id')
                | self.line_ids.mapped('matched_credit_ids.credit_move_id.payment_id')
            )
            for pay in reconciled_payments.filtered(lambda p: p.id):
                result.append({
                    'type': 'payment',
                    'payment_order': 999999,
                    'is_warranty': False,
                    'name': pay.memo if hasattr(pay, 'memo') else (pay.ref or ''),
                    'amount': pay.amount,
                    'currency': pay.currency_id.name,
                    'check_number': pay.name or '',
                    'date': pay.date,
                    'bank': pay.journal_id.name or '',
                })

        # ── PDC payments ─────────────────────────────────────────────────
        pdc_ids = getattr(self, 'pdc_payment_ids', None)
        if pdc_ids:
            for pdc in pdc_ids:
                is_warranty = getattr(pdc, 'is_warranty_cheque', False)

                if include_warranty and not is_warranty:
                    continue
                if not include_warranty and is_warranty:
                    continue

                # state filter
                state = pdc.state
                if is_warranty:
                    if state not in ('registered', 'deposited', 'done'):
                        continue
                else:
                    if state not in ('deposited', 'done'):
                        continue

                result.append({
                    'type': 'pdc',
                    'payment_order': getattr(pdc, 'payment_order', 999999) or 999999,
                    'is_warranty': is_warranty,
                    'name': getattr(pdc, 'memo', '') or '',
                    'amount': getattr(pdc, 'payment_amount', 0.0),
                    'currency': pdc.currency_id.name,
                    'check_number': getattr(pdc, 'reference', '') or '',
                    'date': getattr(pdc, 'due_date', None),
                    'bank': pdc.bank_id.name if getattr(pdc, 'bank_id', None) else '',
                })

        result.sort(key=lambda x: (x['payment_order'],))
        return result
