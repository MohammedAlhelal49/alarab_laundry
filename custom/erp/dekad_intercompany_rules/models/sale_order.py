# -*- coding: utf-8 -*-
from odoo import api, models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """ Override: auto-fill the Order Confirm Date tracking field on all
            linked pickings (and their moves) when the SO is confirmed.
            (from dekad_stock_tracking)
        """
        res = super().action_confirm()
        now = fields.Datetime.now()
        for order in self:
            for picking in order.picking_ids:
                if not picking.x_order_confirm_date:
                    picking.write({'x_order_confirm_date': now})
                    # نفس القيمة على الـ moves
                    picking.move_ids.write({'x_order_confirm_date': now})
        return res

    def _action_confirm(self):
        """ Override: when an intercompany SO is confirmed, lock the source PO
            (set state to 'done') so that:
            - PO lines become read-only
            - The Cancel button is no longer available to the buying company
            - The Unlock button is hidden
        """
        res = super()._action_confirm()
        self._intercompany_sync_po_lock()
        return res

    def action_cancel(self):
        """ Override: when an intercompany SO is cancelled, unlock the source PO
            back to 'purchase' state so the buying company can manage it again.
        """
        res = super().action_cancel()
        self._intercompany_sync_po_unlock()
        return res

    def action_draft(self):
        """ Override: when an intercompany SO is reset to draft, unlock the
            source PO back to 'purchase' state.
        """
        res = super().action_draft()
        self._intercompany_sync_po_unlock()
        return res

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _intercompany_sync_po_lock(self):
        """ Lock the PO(s) linked to self (as intercompany source). """
        pos = self._get_intercompany_source_pos()
        if pos:
            pos.sudo().write({'state': 'done', 'intercompany_locked': True})

    def _intercompany_sync_po_unlock(self):
        """ Unlock the PO(s) linked to self back to 'purchase' state. """
        pos = self._get_intercompany_source_pos()
        if pos:
            pos.sudo().filtered(
                lambda p: p.state == 'done' and p.intercompany_locked
            ).write({'state': 'purchase', 'intercompany_locked': False})

    def _get_intercompany_source_pos(self):
        """ Return the source PO recordset for all SO in self that were
            auto-generated from an intercompany PO.
        """
        pos = self.env['purchase.order']
        for order in self:
            if order.auto_purchase_order_id:
                pos |= order.auto_purchase_order_id.sudo()
        return pos

    @api.model
    def _prepare_purchase_order_line_data(self, so_line, date_order, company):
        """ Override: pass through the tax configuration of the SO line to the
            generated PO line.

            Mirrors the PO -> SO override in purchase_order.py:
            - SO line has taxes  -> PO line gets the same taxes.
            - SO line has NO tax -> PO line is created with NO tax.
        """
        vals = super()._prepare_purchase_order_line_data(so_line, date_order, company)
        # Only override taxes when the SO line explicitly has NO tax.
        # If SO line has taxes, leave vals untouched so Odoo auto-computes
        # the matching taxes for the PO company.
        if not so_line.tax_id:
            vals['taxes_id'] = [(5, 0, 0)]
        return vals
