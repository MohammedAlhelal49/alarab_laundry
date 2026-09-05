# -*- coding: utf-8 -*-
from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    # ------------------------------------------------------------------ #
    #  Shipment Tracking Fields (from dekad_stock_tracking)               #
    # ------------------------------------------------------------------ #

    x_order_confirm_date = fields.Datetime(
        string='Order Confirm Date',
        copy=False,
    )
    x_preparing_order_date = fields.Datetime(
        string='Preparing Order Date',
        copy=False,
    )
    x_shipping_order_date = fields.Datetime(
        string='Shipping Order Date',
        copy=False,
    )
    x_shipment_delivery_date = fields.Datetime(
        string='Shipment Delivery Date',
        copy=False,
    )
    x_shipment_company = fields.Char(
        string='Shipment Company',
        copy=False,
    )
    x_shipment_method = fields.Char(
        string='Shipment Method',
        copy=False,
    )
    x_is_intercompany_dest = fields.Boolean(
        string='Is Intercompany Destination',
        default=False,
        copy=False,
    )

    TRACKING_FIELDS = [
        'x_order_confirm_date',
        'x_preparing_order_date',
        'x_shipping_order_date',
        'x_shipment_delivery_date',
        'x_shipment_company',
        'x_shipment_method',
    ]

    # ------------------------------------------------------------------ #
    #  On create: inherit intercompany flag from picking                  #
    # ------------------------------------------------------------------ #

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for move in records:
            # لما الـ move يتولد، إذا الـ picking تبعه هو intercompany dest
            # نضبط الـ flag على الـ move أيضاً تلقائياً
            if move.picking_id and move.picking_id.x_is_intercompany_dest:
                move.sudo().with_context(
                    skip_intercompany_sync=True
                ).write({'x_is_intercompany_dest': True})
                _logger.info(
                    "Move %s inherited x_is_intercompany_dest from picking %s",
                    move.id, move.picking_id.name,
                )
        return records

    # ------------------------------------------------------------------ #
    #  Find linked dest move at buying company                            #
    # ------------------------------------------------------------------ #

    def _get_intercompany_dest_move(self):
        self.ensure_one()
        if not self.picking_id or not self.picking_id.sale_id:
            return self.env['stock.move']

        purchase_order = self.env['purchase.order'].sudo().search([
            ('name', '=', self.picking_id.sale_id.client_order_ref),
        ], limit=1)

        if not purchase_order:
            return self.env['stock.move']

        receipts = purchase_order.picking_ids.filtered(
            lambda p: p.picking_type_code in ('incoming', 'dropship')
        )

        return receipts.move_ids.filtered(
            lambda m: m.product_id == self.product_id
        )

    # ------------------------------------------------------------------ #
    #  Sync to dest move                                                  #
    # ------------------------------------------------------------------ #

    def _sync_tracking_to_dest(self, vals):
        sync_vals = {k: v for k, v in vals.items() if k in self.TRACKING_FIELDS}
        if not sync_vals:
            return
        for move in self:
            if move.x_is_intercompany_dest:
                continue
            dest_moves = move._get_intercompany_dest_move()
            if dest_moves:
                dest_moves.sudo().with_context(
                    skip_intercompany_sync=True
                ).write(sync_vals)
                _logger.info(
                    "Synced move %s → dest moves %s",
                    move.id, dest_moves.ids,
                )

    def write(self, vals):
        res = super().write(vals)

        # نشر القيم من stock.move → stock.move.line
        propagate_vals = {k: v for k, v in vals.items() if k in self.TRACKING_FIELDS}
        if propagate_vals:
            for move in self:
                if move.move_line_ids:
                    move.move_line_ids.with_context(
                        skip_intercompany_sync=True
                    ).write(propagate_vals)

        # مزامنة مع الـ Receipt عند UAE
        if not self.env.context.get('skip_intercompany_sync'):
            self._sync_tracking_to_dest(vals)

        return res

    # ------------------------------------------------------------------ #
    #  Intercompany receipt quantity lock (from dekad_intercompany_rules) #
    # ------------------------------------------------------------------ #

    @api.depends('product_id', 'picking_id', 'picking_id.purchase_id')
    def _compute_is_quantity_done_editable(self):
        """ Override: make the done quantity read-only on Receipt moves that
            belong to an intercompany Purchase Order (i.e. auto-generated from
            a Sale Order in another company via inter-company rules).

            Default Odoo behaviour:
                move.is_quantity_done_editable = move.product_id
            (always editable as long as a product is set)

            Our behaviour:
            - Intercompany Receipt  → is_quantity_done_editable = False (locked)
            - All other moves       → default behaviour (unchanged)

            The chain that identifies an intercompany receipt:
                stock.move
                  → picking_id (stock.picking)
                    → purchase_id (purchase.order)   [from purchase_stock]
                      → auto_sale_order_id (sale.order) [from sale_purchase_inter_company_rules]
        """
        super()._compute_is_quantity_done_editable()
        for move in self:
            if (
                move.picking_id
                and move.picking_id.picking_type_code == 'incoming'
                and move.picking_id.purchase_id
            ):
                po = move.picking_id.purchase_id
                # Check if this PO was the source for an intercompany SO
                # (sale.order.auto_purchase_order_id points back to this PO)
                intercompany_so = self.env['sale.order'].sudo().search([
                    ('auto_purchase_order_id', '=', po.id)
                ], limit=1)
                if intercompany_so:
                    move.is_quantity_done_editable = False
