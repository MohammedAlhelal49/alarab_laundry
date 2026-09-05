from odoo import models, fields
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero
from markupsafe import Markup
import logging

_logger = logging.getLogger(__name__)


class StockLandedCostCancel(models.Model):
    """
    Landed Cost Cancel Module — handles one specific case only:

    Requirements:
        - LC must be in Done (Posted) state
        - No stock movements out of inventory (remaining_qty == original_qty)
        - Accounting period must be open (not locked)

    Steps:
        1. Reverse Journal Entry
        2. Reverse SVL entries
        3. Recompute product cost (AVCO or FIFO)
        4. Cancel the LC
    """
    _inherit = 'stock.landed.cost'

    # =========================================================
    #  ENTRY POINT
    # =========================================================

    def action_cancel_landed_cost(self):
        """
        Entry point — validates all conditions then executes cancellation.
        Uses Guard Clauses pattern: fail fast before any execution.
        """
        self.ensure_one()

        if self.state == 'cancel':
            return False

        if self.state != 'done':
            raise UserError(
                "Cannot cancel a Landed Cost that has not been validated "
                "(state must be Posted)."
            )

        if self._lcc_is_period_locked():
            raise UserError(
                "The accounting period is locked.\n"
                "Cannot reverse entries in a locked period.\n"
                "Please create a manual corrective journal entry dated today."
            )

        original_qty, remaining_qty = self._lcc_get_qty_summary()

        if original_qty == 0:
            raise UserError(
                f"No stock moves found for this Landed Cost ({self.name})."
            )

        if remaining_qty < original_qty:
            moved_qty = original_qty - remaining_qty
            raise UserError(
                f"Cannot cancel '{self.name}'.\n\n"
                f"This Landed Cost was applied to {original_qty:.0f} unit(s), "
                f"but {moved_qty:.0f} unit(s) have already left the inventory "
                f"(via delivery, transfer, or scrap).\n\n"
                f"Remaining in stock: {remaining_qty:.0f} unit(s)\n\n"

            )

        self._lcc_do_cancel()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    # =========================================================
    #  ENTRY POINT — Correct Button
    # =========================================================

    def action_correct_landed_cost(self):
        """
        Opens the correction wizard.
        Only allowed when no stock has left the inventory.
        """
        self.ensure_one()

        if self.state != 'done':
            raise UserError(
                "Cannot correct a Landed Cost that has not been validated "
                "(state must be Posted)."
            )

        # Guard: no sales allowed
        original_qty, remaining_qty = self._lcc_get_qty_summary()

        if original_qty == 0:
            raise UserError(
                f"No stock moves found for this Landed Cost ({self.name})."
            )

        if remaining_qty < original_qty:
            moved_qty = original_qty - remaining_qty
            raise UserError(
                f"Cannot correct '{self.name}'.\n\n"
                f"This Landed Cost was applied to {original_qty:.0f} unit(s), "
                f"but {moved_qty:.0f} unit(s) have already left the inventory "
                f"(via delivery, transfer, or scrap).\n\n"
                f"Remaining in stock: {remaining_qty:.0f} unit(s)\n\n"

            )

        # current_amount = this LC + all corrective LCs on same pickings
        current_amount = self._lcc_get_effective_amount()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Correct Landed Cost',
            'res_model': 'correct.landed.cost.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_landed_cost_id': self.id,
                'default_current_amount': current_amount,
                'default_split_method': (
                    self.cost_lines[0].split_method
                    if self.cost_lines else 'by_quantity'
                ),
            },
        }

    def _lcc_get_effective_amount(self):
        """
        Returns the total effective LC amount applied on the same pickings.

        Sums this LC + all other validated LCs on the same pickings
        that were created as corrections (name contains 'Correction of').

        This ensures current_amount in the wizard is always up to date
        even after multiple corrections.
        """
        original = sum(self.cost_lines.mapped('price_unit'))

        # Find all corrective LCs on same pickings
        corrective_lcs = self.env['stock.landed.cost'].search([
            ('picking_ids', 'in', self.picking_ids.ids),
            ('state', '=', 'done'),
            ('id', '!=', self.id),
            ('cost_lines.name', 'like', f'Correction of {self.name}'),
        ])

        corrections = sum(
            sum(lc.cost_lines.mapped('price_unit'))
            for lc in corrective_lcs
        )

        _logger.info(
            "Effective amount for %s: original=%.2f corrections=%.2f total=%.2f",
            self.name, original, corrections, original + corrections
        )

        return original + corrections

    # =========================================================
    #  CORE CORRECTION LOGIC
    # =========================================================

    def _lcc_do_correct(self, correct_amount, split_method):
        """
        Creates a corrective LC with the diff value.

        Guards:
            1. correct_amount > 0 (enforced in wizard)
            2. No product cost drops below pre-LC value (enforced here)

        diff > 0 → increases cost (under-charged)
        diff < 0 → decreases cost (over-charged)
        """
        self.ensure_one()

        current_amount = self._lcc_get_effective_amount()
        diff = correct_amount - current_amount

        _logger.info(
            "LC Correct: %s | current=%.2f | correct=%.2f | diff=%.2f",
            self.name, current_amount, correct_amount, diff
        )

        # Guard 2: no product cost below pre-LC floor
        if diff < 0:
            self._lcc_check_cost_floor(diff)

        new_lc = self._lcc_create_corrective_lc(diff, split_method)

        self.message_post(
            body=Markup(
                f"<b>Landed Cost Corrected</b>"
                f"<ul>"
                f"<li>Previous amount: <b>{current_amount:.2f}</b></li>"
                f"<li>Correct amount: <b>{correct_amount:.2f}</b></li>"
                f"<li>Difference: <b>{diff:+.2f}</b></li>"
                f"<li>Corrective LC: <b>{new_lc.name}</b></li>"
                f"</ul>"
            )
        )

    def _lcc_check_cost_floor(self, diff):
        """
        Ensures no product cost drops below its pre-LC value.

        Logic:
            The LC created SVL records linked to parent layers.
            parent_layer.remaining_value currently includes the LC value.
            cost_before_lc = (parent.remaining_value - svl.value)
                             / parent.remaining_qty

            After correction:
            cost_after = (parent.remaining_value + diff_for_svl)
                         / parent.remaining_qty

            We require: cost_after >= cost_before_lc
            Which means: diff_for_svl >= -svl.value

        Raises:
            UserError if any product would drop below pre-LC cost.
        """
        total_lc = sum(self.stock_valuation_layer_ids.mapped('value'))
        if not total_lc:
            return

        errors = []

        for svl in self.stock_valuation_layer_ids:
            parent  = svl.stock_valuation_layer_id
            product = svl.product_id

            if not parent or not parent.remaining_qty:
                continue

            svl_ratio    = svl.value / total_lc
            diff_for_svl = diff * svl_ratio

            value_before   = parent.remaining_value - svl.value
            cost_before_lc = value_before / parent.remaining_qty

            value_after = parent.remaining_value + diff_for_svl
            cost_after  = value_after / parent.remaining_qty

            _logger.info(
                "Cost floor check — %s: before_lc=%.4f | after=%.4f",
                product.name, cost_before_lc, cost_after
            )

            if cost_after < cost_before_lc:
                errors.append(
                    f"• {product.name}: "
                    f"cost after correction {cost_after:.2f} "
                    f"< original cost {cost_before_lc:.2f}"
                )

        if errors:
            min_amount = self._lcc_min_correct_amount()
            error_lines = "\n".join(errors)
            raise UserError(
                f"Cannot apply this correction — the following products "
                f"would drop below their pre-LC cost:\n\n"
                f"{error_lines}\n\n"
                f"Minimum allowed correct amount: {min_amount:.2f}"
            )

    def _lcc_min_correct_amount(self):
        """
        Calculates the minimum correct_amount that keeps all
        product costs at or above their pre-LC values.

        Math:
            For each SVL: diff_for_svl >= -svl.value
            diff * svl_ratio >= -svl.value
            diff >= -svl.value / svl_ratio
            diff >= -total_lc

            Minimum diff = max of all per-SVL floors
            min_correct  = current_amount + min_diff
        """
        current_amount = sum(self.cost_lines.mapped('price_unit'))
        total_lc       = sum(self.stock_valuation_layer_ids.mapped('value'))

        if not total_lc:
            return current_amount

        min_diff = -total_lc  # theoretical floor

        for svl in self.stock_valuation_layer_ids:
            parent = svl.stock_valuation_layer_id
            if not parent or not parent.remaining_qty or not total_lc:
                continue

            svl_ratio = svl.value / total_lc
            if svl_ratio:
                floor_diff = -svl.value / svl_ratio
                if floor_diff > min_diff:
                    min_diff = floor_diff

        return max(0.0, current_amount + min_diff)



    def _lcc_create_corrective_lc(self, amount, split_method):
        """
        Creates a new corrective LC linked to the same pickings.
        amount > 0 → increases cost (under-charged)
        amount < 0 → decreases cost (over-charged)
        """
        if not self.cost_lines:
            raise UserError("No cost lines found on this Landed Cost.")

        product = self.cost_lines[0].product_id
        account = self.cost_lines[0].account_id

        new_lc = self.env['stock.landed.cost'].create({
            'date':               fields.Date.today(),
            'account_journal_id': self.account_journal_id.id,
            'picking_ids':        [(6, 0, self.picking_ids.ids)],
        })

        self.env['stock.landed.cost.lines'].create({
            'cost_id':      new_lc.id,
            'name':         f'Correction of {self.name}',
            'product_id':   product.id,
            'price_unit':   amount,
            'split_method': split_method,
            'account_id':   account.id,
        })

        new_lc.compute_landed_cost()
        new_lc.button_validate()

        # Add ref to the Journal Entry for traceability
        if new_lc.account_move_id:
            new_lc.account_move_id.ref = f'Corrective LC for {self.name}'

        _logger.info(
            "Corrective LC created: %s | amount=%.2f",
            new_lc.name, amount
        )
        return new_lc



    # =========================================================
    #  CORE CANCEL LOGIC
    # =========================================================

    def _lcc_do_cancel(self):
        """
        Executes the full cancellation in 5 sequential steps.

        Step 0 (new): Reverse any corrective LCs first.
        This ensures product cost returns to its true pre-LC value
        even if corrections were applied after the original LC.
        """
        self.ensure_one()
        _logger.info("LC Cancel starting: %s", self.name)

        # ── Step 0: Reverse corrective LCs first ───────────
        # Find all corrective LCs on same pickings
        corrective_lcs = self.env['stock.landed.cost'].search([
            ('picking_ids', 'in', self.picking_ids.ids),
            ('state', '=', 'done'),
            ('id', '!=', self.id),
            ('cost_lines.name', 'like', f'Correction of {self.name}'),
        ])

        if corrective_lcs:
            _logger.info(
                "Reversing %d corrective LC(s) before cancelling %s",
                len(corrective_lcs), self.name
            )
            for clc in corrective_lcs:
                clc._lcc_reverse_single(
                    ref_suffix='— Parent LC Cancelled'
                )

        # ── Steps 1-3: Reverse JE + SVL + cost ────────────
        self._lcc_reverse_single(ref_suffix='— LC Cancelled')

        # ── Step 4: Log in Chatter ─────────────────────────
        corrective_names = corrective_lcs.mapped('name') if corrective_lcs else []
        body = (
            f"<b>Landed Cost Cancelled</b>"
            f"<ul>"
            f"<li>Cancelled on: <b>{fields.Date.today()}</b></li>"
            f"<li>SVL entries reversed.</li>"
            f"<li>Product cost restored.</li>"
        )
        if corrective_names:
            body += f"<li>Also reversed corrective LC(s): <b>{', '.join(corrective_names)}</b></li>"
        body += "</ul>"

        self.message_post(body=Markup(body))
        _logger.info("LC Cancel completed: %s", self.name)

    def _lcc_reverse_single(self, ref_suffix='— Reversed'):
        """
        Reverses a single LC's JE + SVL + cost.
        Used both for direct cancel and for reversing corrective LCs
        before cancelling the original.
        """
        self.ensure_one()

        # Reverse JE
        move = self.account_move_id
        if move and move.state == 'posted':
            reversal = move._reverse_moves(
                default_values_list=[{
                    'date': fields.Date.today(),
                    'ref': f'Reversal of {move.name} {ref_suffix}',
                }]
            )
            reversal.action_post()

        # Reverse SVL
        svl_records = self.stock_valuation_layer_ids
        if svl_records:
            for svl in svl_records:
                self.env['stock.valuation.layer'].create({
                    'product_id':           svl.product_id.id,
                    'quantity':             0.0,
                    'uom_id':               svl.uom_id.id,
                    'value':                -svl.value,
                    'remaining_qty':        0.0,
                    'remaining_value':      0.0,
                    'description':          f'Reversal of LC {self.name} {ref_suffix}',
                    'stock_move_id':        svl.stock_move_id.id,
                    'company_id':           svl.company_id.id,
                    'stock_landed_cost_id': self.id,
                })

            # Recompute cost
            affected_products = (
                svl_records.mapped('product_id').with_company(self.company_id)
            )
            for product in affected_products:
                lc_value = sum(
                    svl.value for svl in svl_records
                    if svl.product_id == product
                )
                self._lcc_recompute_cost(product, lc_value)

        self.write({'state': 'cancel'})

    # =========================================================
    #  COST RECOMPUTATION — AVCO and FIFO
    # =========================================================

    def _lcc_recompute_cost(self, product, lc_value):
        """
        Restores the product cost after reversing the LC.

        AVCO:
            Mirrors the reverse of button_validate:
            standard_price -= lc_value / quantity_svl

        FIFO:
            Each incoming layer has its own cost.
            The LC added value to each parent layer's remaining_value.
            We reverse by subtracting from the same parent layer
            using svl.stock_valuation_layer_id (direct reference).
            Then recalculate standard_price from the oldest remaining layer.

        Args:
            product (product.product): The affected product
            lc_value (float): Total LC value for this product (positive)
        """
        costing_method = product.categ_id.property_cost_method

        if costing_method == 'average':
            # ── AVCO ──────────────────────────────────────
            if not float_is_zero(
                product.quantity_svl,
                precision_rounding=product.uom_id.rounding
            ):
                cost_reduction = lc_value / product.quantity_svl
                product.sudo().with_context(
                    disable_auto_svl=True
                ).standard_price -= cost_reduction
                _logger.info(
                    "AVCO: %s standard_price -= %.4f",
                    product.name, cost_reduction
                )

        elif costing_method == 'fifo':
            # ── FIFO — layer by layer ──────────────────────
            # During button_validate, Odoo does:
            #   linked_layer[:1].remaining_value += cost_to_add
            # So we reverse by subtracting from the same parent layer.
            product_svl = self.stock_valuation_layer_ids.filtered(
                lambda s: s.product_id == product
            )

            if not product_svl:
                _logger.warning("FIFO: no SVL records for %s", product.name)
                return

            for svl in product_svl:
                if svl.stock_valuation_layer_id:
                    parent = svl.stock_valuation_layer_id
                    parent.remaining_value -= svl.value
                    _logger.info(
                        "FIFO parent layer %d: remaining_value -= %.4f",
                        parent.id, svl.value
                    )

            # Recalculate standard_price from oldest remaining layer
            # FIFO rule: oldest stock is used first
            move_ids = []
            for picking in self.picking_ids:
                move_ids += picking.move_ids.ids

            oldest_layer = self.env['stock.valuation.layer'].search([
                ('stock_move_id', 'in', move_ids),
                ('product_id', '=', product.id),
                ('quantity', '>', 0),
                ('remaining_qty', '>', 0),
            ], order='id asc', limit=1)

            if oldest_layer and not float_is_zero(
                oldest_layer.remaining_qty,
                precision_rounding=product.uom_id.rounding
            ):
                new_cost = oldest_layer.remaining_value / oldest_layer.remaining_qty
                product.sudo().with_context(
                    disable_auto_svl=True
                ).standard_price = new_cost
                _logger.info(
                    "FIFO: %s new standard_price = %.4f",
                    product.name, new_cost
                )
        else:
            _logger.warning(
                "Unsupported costing method '%s' for product %s — skipping.",
                costing_method, product.name
            )

    # =========================================================
    #  HELPERS
    # =========================================================

    def _lcc_is_period_locked(self):
        """
        Checks if the LC's accounting period is locked.

        Note: In Odoo 18, period_lock_date was removed.
        Only fiscalyear_lock_date remains on res.company.

        Returns:
            bool: True if locked, False otherwise
        """
        lock_date = self.company_id.fiscalyear_lock_date
        if not lock_date:
            return False
        move = self.account_move_id
        if move and move.date and move.date <= lock_date:
            return True
        return False

    def _lcc_get_qty_summary(self):
        """
        Computes original and remaining quantities via SVL.

        SVL is used instead of stock.move because it is the actual
        financial ledger — updated automatically on every sale,
        transfer, or inventory adjustment.

        Returns:
            tuple: (original_qty, remaining_qty)
                original_qty:  total quantity received
                remaining_qty: quantity still in stock
        """
        move_ids = []
        for picking in self.picking_ids:
            move_ids += picking.move_ids.ids

        if not move_ids:
            return 0.0, 0.0

        svl_records = self.env['stock.valuation.layer'].search([
            ('stock_move_id', 'in', move_ids),
            ('quantity', '>', 0),   # incoming layers only
        ])

        original_qty  = sum(svl_records.mapped('quantity'))
        remaining_qty = sum(svl_records.mapped('remaining_qty'))

        return original_qty, remaining_qty