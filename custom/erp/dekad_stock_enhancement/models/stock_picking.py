# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_add_analytic_distribution_all(self):
        for item in self.search([]):
            item.action_add_analytic_distribution()

    def action_add_analytic_distribution(self):
        for picking in self:
            for move in picking.move_ids:
                move_account_move_lines = move.stock_valuation_layer_ids.mapped('account_move_id').mapped('line_ids')
                if move.analytic_account_id:
                    for line in move_account_move_lines:
                        if line.debit:
                            line.analytic_distribution = {move.analytic_account_id.id: 100.0}

    def unlink(self):
        # Collect related valuation layers BEFORE deletion
        all_valuation_layers = self.env['stock.valuation.layer']

        for rec in self:
            valuation_move_ids = rec.move_ids.stock_valuation_layer_ids

            scrap_moves = self.env['stock.scrap'].search([
                ('picking_id', '=', rec.id)
            ])
            valuation_scrap_ids = scrap_moves.move_ids.stock_valuation_layer_ids

            all_valuation_layers |= (valuation_move_ids | valuation_scrap_ids)

        # Call original unlink (delete picking)
        res = super().unlink()

        # Execute your logic AFTER deletion
        if all_valuation_layers:
            all_valuation_layers.action_delete_related_cancel_journal()

        return res

    def delete_related_cancel_journal(self):
        for rec in self:
            valuation_move_ids = rec.move_ids.stock_valuation_layer_ids

            scrap_moves = self.env['stock.scrap'].search([
                ('picking_id', '=', rec.id)
            ])

            valuation_scrap_ids = scrap_moves.move_ids.stock_valuation_layer_ids

            # Use union instead of +
            valuation_ids = valuation_move_ids | valuation_scrap_ids

            if valuation_ids:
                valuation_ids.action_delete_related_cancel_journal()

    def action_view_valuation(self):
        action = self.env.ref("stock_account.stock_valuation_layer_action").sudo().read()[0]
        action.setdefault("domain", [])
        action_ctx = dict(self._context)
        action_ctx.update({
            "search_default_regular_valuations": 0,
            "search_default_cancel_reversals": 0,
        })
        action["context"] = action_ctx
        return action

    def action_confirm_cancel(self):
        for picking in self.sudo():
            if picking.state == "done":
                # raise UserError(_("Only validated transfers can be cancelled."))
                ctx = dict(self.env.context, mail_notrack=True, tracking_disable=True)
                self = self.with_context(ctx)
                wizard = self.env["dekad.picking.cancel.wizard"].with_context(ctx).create({
                    "picking_ids": [(6, 0, [picking.id])],
                    "option": "cancel_draft",
                })
                wizard.with_context(ctx).action_apply()

                user_name = self.env.user.name
                _logger.info("Picking %s cancelled by %s", picking.name, user_name)
        return True

    def _create_mirror_picking(self, source_picking, target_company, type_code):
        """
        Creates the document in the other company in DRAFT state and logs to both.
        """
        TargetEnv = self.env['stock.picking'].with_company(target_company).sudo()

        # Find the correct Operation Type in the target company
        picking_type = self.env['stock.picking.type'].with_company(target_company).search([
            ('code', '=', type_code),
            ('company_id', '=', target_company.id)
        ], limit=1)

        if not picking_type:
            _logger.warning(">>> ERROR: No %s Picking Type found in %s", type_code, target_company.name)
            return

        # Prepare Moves
        move_vals = []
        for move in source_picking.move_ids_without_package:
            move_vals.append((0, 0, {
                'name': move.product_id.name,
                'product_id': move.product_id.id,
                'product_uom_qty': move.quantity,
                'product_uom': move.product_uom.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': picking_type.default_location_dest_id.id,
                'company_id': target_company.id,
                'state': 'draft',
            }))

        # Create the Picking
        new_picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': source_picking.company_id.partner_id.id,  # The Partner is the Origin Company
            'origin': f"Inter-Company: {source_picking.name}",
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'move_ids_without_package': move_vals,
            'company_id': target_company.id,
            'state': 'draft',
        }

        new_picking = TargetEnv.create(new_picking_vals)

        # --- LOGGING ---

        # 1. Log on the NEW Picking (Target Company)
        new_picking.message_post(
            body=f"This transfer was automatically generated from {source_picking.name} in {source_picking.company_id.name}."
        )

        # 2. Log on the OLD Picking (Source Company)
        source_picking.message_post(
            body=f"Inter-Company Draft transfer created:{new_picking.name} in {target_company.name}."
        )

    def _pre_action_done_hook(self):
        res = super()._pre_action_done_hook()

        if res is not True:
            return res

        for picking in self:
            # Feature disabled for this company -> don't require signature
            if not picking.company_id.require_picking_signature:
                continue

            # Only enforce for users/signature feature as before
            if not self.env.user.has_group('stock.group_stock_sign_delivery'):
                continue

            if (
                    picking.picking_type_code in ('outgoing', 'internal')
                    and not picking.signature
            ):
                raise UserError(_(
                    'يجب أخذ توقيع المستلم قبل التأكيد:\n%s',
                    picking.name
                ))

        return res


    def _attach_sign(self):
        """
        Override to delay PDF generation until after Validate (state == done).
        If the user signs before validating, the PDF will be generated automatically
        after _action_done via _action_done override below.
        """
        self.ensure_one()
        if self.state != 'done':
            return True
        return super()._attach_sign()


    def _action_done(self):
        # 1. Standard Odoo validation
        for picking in self:
            if picking.scheduled_date:
                picking.write({'date_done': picking.scheduled_date})
        res = super(StockPicking, self)._action_done()

        for picking in self:
            if picking.scheduled_date:
                picking.write({'date_done': picking.scheduled_date})

        # Generate signed PDF for pickings that were signed before Validate
        for picking in self:
            if picking.signature:
                picking._attach_sign()

        for picking in self:
            picking.action_add_analytic_distribution()
            # LOOP BREAKER: If this picking was created by our script (has prefix), stop.
            if picking.origin and "Inter-Company" in picking.origin:
                continue

            # 2. Identify the Target Company from the Partner
            target_company = self.env['res.company'].sudo().search([
                ('partner_id', '=', picking.partner_id.id)
            ], limit=1)

            if not target_company or target_company == picking.company_id:
                continue

            # 3. DIRECTION 1: Outgoing (Delivery A -> Receipt B)
            if picking.picking_type_code == 'outgoing' and target_company.auto_inv_receipt:
                self._create_mirror_picking(picking, target_company, 'incoming')

            # 4. DIRECTION 2: Incoming (Receipt A -> Delivery B)
            elif picking.picking_type_code == 'incoming' and target_company.auto_inv_delivery:
                self._create_mirror_picking(picking, target_company, 'outgoing')

        return res
