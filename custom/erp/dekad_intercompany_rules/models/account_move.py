# -*- coding: utf-8 -*-
from odoo import models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _inter_company_create_invoices(self):
        """ Override: preserve the "no tax" state of the source invoice line
            when generating the counterpart invoice in the other company.

            Default Odoo behaviour (account_inter_company_rules) always runs
            `line.tax_ids = line._get_computed_taxes()` on every product line
            of the new invoice, which re-applies the default taxes coming from
            the fiscal position / product - even if the original line had no
            tax at all.

            This override is a full copy of the original method with a single
            targeted change: the recompute is skipped for lines whose source
            (`inv` / self) line had no tax_ids to begin with, so those lines
            stay tax-free on the generated invoice. Lines that DO have a tax
            keep the original (default) auto-compute behaviour.
        """
        invoices_vals_per_type = {}
        inverse_types = {
            'out_invoice': 'in_invoice',
            'out_refund': 'in_refund',
        }
        for inv in self:
            invoice_vals = inv._inter_company_prepare_invoice_data(inverse_types[inv.move_type])
            invoice_vals['invoice_line_ids'] = []

            # Build a mapping: sequence → had_no_tax, based only on product lines
            # (skip sections/notes which don't have tax_ids at all)
            source_product_lines = inv.invoice_line_ids.filtered(
                lambda l: l.display_type not in ('line_note', 'line_section')
            )
            no_tax_by_sequence = {
                line.sequence: not line.tax_ids
                for line in source_product_lines
            }

            for line in inv.invoice_line_ids:
                invoice_vals['invoice_line_ids'].append(
                    (0, 0, line._inter_company_prepare_invoice_line_data())
                )

            inv_new = inv.with_context(default_move_type=invoice_vals['move_type']).new(invoice_vals)

            for line in inv_new.invoice_line_ids:
                if line.display_type in ('line_note', 'line_section'):
                    continue

                source_had_no_tax = no_tax_by_sequence.get(line.sequence, False)

                if source_had_no_tax:
                    # keep the line tax-free
                    line.tax_ids = [(5, 0, 0)]
                    continue

                # adapt taxes following fiscal position, keep price unit
                price_unit = line.price_unit
                line.tax_ids = line._get_computed_taxes()
                line.price_unit = price_unit

            invoice_vals = inv_new._convert_to_write(inv_new._cache)
            invoice_vals.pop('line_ids', None)
            invoice_vals['origin_invoice'] = inv

            invoices_vals_per_type.setdefault(invoice_vals['move_type'], [])
            invoices_vals_per_type[invoice_vals['move_type']].append(invoice_vals)

        # Create invoices.
        moves = self.env['account.move']
        for invoice_type, invoices_vals in invoices_vals_per_type.items():
            for invoice in invoices_vals:
                origin_invoice = invoice['origin_invoice']
                invoice.pop('origin_invoice')
                msg = _(
                    "Automatically generated from %(origin)s of company %(company)s.",
                    origin=origin_invoice.name,
                    company=origin_invoice.company_id.name,
                )
                am = self.with_context(default_type=invoice_type).create(invoice)
                am.message_post(body=msg)
                if self.env.company.intercompany_document_state == "posted":
                    am._post(soft=True)
                moves += am
        return moves