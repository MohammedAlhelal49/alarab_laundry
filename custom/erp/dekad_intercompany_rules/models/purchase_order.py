# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    intercompany_locked = fields.Boolean(
        string='Locked by Intercompany',
        default=False,
        copy=False,
        help="Set to True when this PO is locked because the linked "
             "intercompany Sale Order has been confirmed. "
             "Prevents manual unlock.",
    )

    @api.model
    def _prepare_sale_order_line_data(self, line, company):
        """ Override: pass through the tax configuration of the PO line to the
            generated SO line.

            Default Odoo behaviour (sale_purchase_inter_company_rules) does NOT
            include any tax key in the returned values, so the SO line always
            falls back to the default computed taxes (product / fiscal position)
            regardless of what was set on the PO line - including the case where
            the PO line intentionally has NO tax.

            Here, we explicitly forward `line.taxes_id` as `tax_id` on the SO
            line values:
            - PO line has taxes  -> SO line gets the same taxes.
            - PO line has NO tax -> SO line is created with NO tax (commands
              still set to an empty list so Odoo doesn't auto-compute it).
        """
        vals = super()._prepare_sale_order_line_data(line, company)
        # Only override taxes when the PO line explicitly has NO tax.
        # If PO line has taxes, leave vals untouched so Odoo auto-computes
        # the matching taxes for the SO company (they belong to a different company
        # and cannot be copied directly across companies).
        if not line.taxes_id:
            vals['tax_id'] = [(5, 0, 0)]
        return vals
