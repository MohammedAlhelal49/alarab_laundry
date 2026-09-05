# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class DekadPickingCancelWizard(models.TransientModel):
    _name = "dekad.picking.cancel.wizard"
    _description = "Cancel to Draft (and Delete) with zeroing quantities"

    option = fields.Selection(
        [
            ("cancel_draft", "Cancel → Draft"),
            #("cancel_draft_delete", "Cancel → Draft → Delete"),
        ],
        string="Operation",
        required=True,
        default="cancel_draft",
    )

    picking_ids = fields.Many2many(
        "stock.picking",
        string="Pickings",
        default=lambda self: self._default_pickings(),
    )

    @api.model
    def _default_pickings(self):
        ids = self.env.context.get("default_picking_ids") or self.env.context.get("active_ids") or []
        return [(6, 0, ids)]

    # ================= Helpers =================

    def _unreserve_safely(self, picking):
        if hasattr(picking, "action_unreserve"):
            try:
                picking.sudo().action_unreserve()
            except Exception as e:
                _logger.warning("Unreserve failed on %s: %s", picking.name, e)

        for move in picking.move_ids:
            try:
                if hasattr(move, "_do_unreserve"):
                    move.sudo()._do_unreserve()
                elif hasattr(move, "action_unreserve"):
                    move.sudo().action_unreserve()
            except Exception as e:
                _logger.warning("Move unreserve failed on %s: %s", move.name, e)

    def _backup_quantities(self, picking):
        """Store current quantities before they are zeroed out."""
        for move in picking.move_ids.sudo():
            move.write({
                'backup_quantity': move.quantity,
                'backup_product_uom_qty': move.product_uom_qty,
            })

    def _restore_quantities(self, picking):
        """Restore quantities from backup fields."""
        for move in picking.move_ids.sudo():
            if move.backup_quantity or move.backup_product_uom_qty:
                move.write({
                    'quantity': move.backup_quantity,
                    'product_uom_qty': move.backup_product_uom_qty,
                })

    def _zero_quantities(self, picking):
        moves = picking.move_ids
        for line in moves.mapped("move_line_ids"):
            vals = {}
            if "qty_done" in line._fields:
                vals["qty_done"] = 0
            if "product_uom_qty" in line._fields:
                vals["product_uom_qty"] = 0
            if "reserved_uom_qty" in line._fields:
                vals["reserved_uom_qty"] = 0
            if vals:
                line.sudo().write(vals)

        if moves and "product_uom_qty" in self.env["stock.move"]._fields:
            try:
                moves.sudo().write({"product_uom_qty": 0})
            except Exception as e:
                _logger.warning("Failed zero product_uom_qty: %s", e)

        if moves and "quantity" in self.env["stock.move"]._fields:
            try:
                moves.sudo().write({"quantity": 0})
            except Exception:
                ids = [m.id for m in moves]
                if ids:
                    self.env.cr.execute(
                        "UPDATE stock_move SET quantity = 0 WHERE id = ANY(%s)",
                        [ids],
                    )

    def _force_draft_state(self, picking):
        # unlock if needed
        if "is_locked" in picking._fields and picking.is_locked:
            picking.sudo().write({"is_locked": False})

        moves_all = (picking.move_ids_without_package | picking.move_ids).sudo()

        ctx_cancel = dict(self.env.context, from_cancel_wizard=True, mark_as_cancel_reversal=True)
        try:
            if hasattr(picking, "action_cancel"):
                picking.with_context(ctx_cancel).sudo().action_cancel()
        except Exception as e:
            _logger.warning("Cancel picking failed on %s: %s", picking.name, e)

        ctx_write = dict(self.env.context, mail_notrack=True, tracking_disable=True)

        if "state" in self.env["stock.move"]._fields and moves_all:
            moves_all.with_context(ctx_write).write({"state": "draft"})

        vals_pick = {"state": "draft"}
        if "date_done" in picking._fields:
            vals_pick["date_done"] = False
        if "is_locked" in picking._fields:
            vals_pick["is_locked"] = False

        picking.with_context(ctx_write).sudo().write(vals_pick)
        self.env.invalidate_all()

    def _mark_reversal_layers(self, picking):
        svls = self.env["stock.valuation.layer"].sudo().search([
            ("stock_move_id", "in", picking.move_ids.ids)
        ])
        if svls:
            svls.write({"is_cancel_reversal": True})
            _logger.info(
                "Marked %s valuation layers as cancel reversal for picking %s",
                len(svls), picking.name
            )

    # ================= Entry =================

    def action_apply(self):
        if not self.picking_ids:
            raise UserError("No transfers selected.")

        deleted = False

        for picking in self.picking_ids.sudo():
            self._unreserve_safely(picking)
            self._backup_quantities(picking)
            self._zero_quantities(picking)
            self._force_draft_state(picking)
            self._restore_quantities(picking)
            self._mark_reversal_layers(picking)

            if self.option == "cancel_draft_delete":
                picking.sudo().unlink()
                deleted = True

        if deleted:
            action = self.env.ref("stock.action_picking_tree_all", raise_if_not_found=False)
            if action:
                return action.read()[0]

            return {
                "type": "ir.actions.act_window",
                "name": "Transfers",
                "res_model": "stock.picking",
                "view_mode": "tree,form",
                "target": "current",
            }

        return {"type": "ir.actions.act_window_close"}
