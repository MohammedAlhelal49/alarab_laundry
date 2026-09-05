# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ------------------------------------------------------------------ #
    #  Shipment Tracking Fields (from dekad_stock_tracking)               #
    # ------------------------------------------------------------------ #

    x_order_confirm_date = fields.Datetime(
        string='Order Confirm Date',
        tracking=True,
        copy=False,
    )
    x_preparing_order_date = fields.Datetime(
        string='Preparing Order Date',
        tracking=True,
        copy=False,
    )
    x_shipping_order_date = fields.Datetime(
        string='Shipping Order Date',
        tracking=True,
        copy=False,
    )
    x_shipment_delivery_date = fields.Datetime(
        string='Shipment Delivery Date',
        tracking=True,
        copy=False,
    )
    x_shipment_company = fields.Char(
        string='Shipment Company',
        tracking=True,
        copy=False,
    )
    x_shipment_method = fields.Char(
        string='Shipment Method',
        tracking=True,
        copy=False,
    )

    # ------------------------------------------------------------------ #
    #  Intercompany Tracking Fields (from dekad_stock_tracking)           #
    # ------------------------------------------------------------------ #

    x_is_intercompany_dest = fields.Boolean(
        string='Is Intercompany Destination',
        default=False,
        copy=False,
    )
    # الحقل الوحيد للربط — UAE يحدده
    x_source_delivery_id = fields.Many2one(
        'stock.picking',
        string='Source Delivery',
        domain=[('picking_type_code', '=', 'outgoing')],
        copy=False,
        help='The China delivery linked to this receipt.',
    )

    PROPAGATE_FIELDS = [
        'x_preparing_order_date',
        'x_shipping_order_date',
        'x_shipment_delivery_date',
        'x_shipment_company',
        'x_shipment_method',
    ]

    TRACKING_FIELDS = [
        'x_order_confirm_date',
        'x_preparing_order_date',
        'x_shipping_order_date',
        'x_shipment_delivery_date',
        'x_shipment_company',
        'x_shipment_method',
    ]

    # ------------------------------------------------------------------ #
    #  Auto-link on create                                                 #
    # ------------------------------------------------------------------ #

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._setup_intercompany()
        return records

    def _setup_intercompany(self):
        """
        لما يتولد Receipt جديد:
        1. نحدد إذا هو intercompany dest
        2. نربطه تلقائياً بالـ Delivery المقابل
        """
        for picking in self:
            if picking.picking_type_code not in ('incoming', 'dropship'):
                continue
            if not picking.partner_id:
                continue

            # هل الـ partner هو شركة أخرى؟
            sale_company = self.env['res.company'].sudo().search([
                ('partner_id', '=', picking.partner_id.id)
            ], limit=1)

            if not sale_company or sale_company == picking.company_id:
                continue

            # ضبط الـ flag
            picking.sudo().write({'x_is_intercompany_dest': True})
            picking.move_ids.sudo().write({'x_is_intercompany_dest': True})

            # ربط تلقائي بالـ Delivery المقابل
            self._auto_link_delivery(picking, sale_company)

    def _auto_link_delivery(self, receipt, sale_company):
        """
        نلاقي الـ Delivery المقابل للـ Receipt:
        - Receipt أول (بدون backorder) → Delivery أول (بدون backorder)
        - Backorder Receipt → ما نربط تلقائياً (UAE يختار يدوياً)
        """
        # الـ Backorder Receipt لا نربطه تلقائياً
        if receipt.backorder_id:
            return

        if not receipt.purchase_id:
            return

        so_name = receipt.purchase_id.partner_ref
        sale_order = self.env['sale.order'].sudo().search([
            ('name', '=', so_name),
        ], limit=1)

        if not sale_order:
            return

        # الـ Delivery الأول = بدون backorder_id
        delivery = sale_order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
            and not p.backorder_id
        )

        if delivery:
            receipt.sudo().write({'x_source_delivery_id': delivery[0].id})
            _logger.info(
                "Auto-linked Receipt %s → Delivery %s",
                receipt.name, delivery[0].name,
            )

    # ------------------------------------------------------------------ #
    #  Onchange: sync when UAE picks a source delivery                    #
    # ------------------------------------------------------------------ #

    @api.onchange('x_source_delivery_id')
    def _onchange_source_delivery_id(self):
        if not self.x_source_delivery_id:
            return
        src = self.x_source_delivery_id
        self.x_order_confirm_date = src.x_order_confirm_date
        self.x_preparing_order_date = src.x_preparing_order_date
        self.x_shipping_order_date = src.x_shipping_order_date
        self.x_shipment_delivery_date = src.x_shipment_delivery_date
        self.x_shipment_company = src.x_shipment_company
        self.x_shipment_method = src.x_shipment_method

    # ------------------------------------------------------------------ #
    #  Propagate Header → moves                                           #
    # ------------------------------------------------------------------ #

    def _propagate_to_moves(self, vals):
        propagate_vals = {k: v for k, v in vals.items() if k in self.PROPAGATE_FIELDS}
        if not propagate_vals:
            return
        for picking in self:
            if picking.move_ids:
                picking.move_ids.with_context(skip_move_propagation=True).write(propagate_vals)

    # ------------------------------------------------------------------ #
    #  Sync Delivery → linked Receipt                                     #
    # ------------------------------------------------------------------ #

    def _get_linked_receipts(self):
        """
        ابحث عن الـ Receipt المقابل للـ Delivery عبر منطق Odoo الأصلي:
        - Delivery الأول → Receipt الأول (بدون backorder)
        - Backorder Delivery → Receipt اللي فيه moves غير picked
        """
        self.ensure_one()
        if not self.sale_id or self.picking_type_code not in ('outgoing', 'dropship'):
            return self.env['stock.picking']

        purchase_order = self.env['purchase.order'].sudo().search([
            ('name', '=', self.sale_id.client_order_ref),
        ], limit=1)

        if not purchase_order:
            return self.env['stock.picking']

        all_receipts = purchase_order.picking_ids.filtered(
            lambda p: p.picking_type_code in ('incoming', 'dropship')
        )

        if not all_receipts:
            return self.env['stock.picking']

        # Backorder Delivery → Receipt اللي فيه moves غير picked
        if self.backorder_id:
            return all_receipts.filtered(
                lambda r: any(not m.picked for m in r.move_ids)
                and r.state not in ('done', 'cancel')
            )

        # Delivery الأول → Receipt الأول (بدون backorder)
        return all_receipts.filtered(lambda r: not r.backorder_id)

    def _sync_to_linked_receipts(self, vals):
        sync_vals = {k: v for k, v in vals.items() if k in self.TRACKING_FIELDS}
        if not sync_vals:
            return
        for picking in self:
            if picking.x_is_intercompany_dest:
                continue
            receipts = picking._get_linked_receipts()
            if receipts:
                receipts.sudo().with_context(
                    skip_intercompany_sync=True
                ).write(sync_vals)
                _logger.info(
                    "Synced %s → receipts %s",
                    picking.name, receipts.mapped('name'),
                )

    # ------------------------------------------------------------------ #
    #  Auto-fill Shipping Date on Validate                                #
    # ------------------------------------------------------------------ #

    def button_validate(self):
        res = super().button_validate()
        now = fields.Datetime.now()
        for picking in self:
            if picking.picking_type_code != 'outgoing':
                continue
            if picking.x_is_intercompany_dest:
                continue
            if not picking.x_shipping_order_date:
                picking.write({'x_shipping_order_date': now})
        return res

    # ------------------------------------------------------------------ #
    #  Backorder: keep confirm date only                                  #
    # ------------------------------------------------------------------ #

    def _create_backorder(self):
        backorders = super()._create_backorder()
        for backorder in backorders:
            if not backorder.backorder_id:
                continue
            confirm_date = backorder.backorder_id.x_order_confirm_date
            backorder.with_context(skip_intercompany_sync=True).write({
                'x_order_confirm_date': confirm_date,
                'x_preparing_order_date': False,
                'x_shipping_order_date': False,
                'x_shipment_delivery_date': False,
                'x_shipment_company': False,
                'x_shipment_method': False,
                'x_source_delivery_id': False,
            })
            backorder.move_ids.with_context(skip_intercompany_sync=True).write({
                'x_order_confirm_date': confirm_date,
                'x_preparing_order_date': False,
                'x_shipping_order_date': False,
                'x_shipment_delivery_date': False,
                'x_shipment_company': False,
                'x_shipment_method': False,
            })
        return backorders

    # ------------------------------------------------------------------ #
    #  Auto-fill confirm date on SO confirm                               #
    # ------------------------------------------------------------------ #

    def _set_order_confirm_date(self, now):
        for picking in self:
            if not picking.x_order_confirm_date:
                picking.write({'x_order_confirm_date': now})

    # ------------------------------------------------------------------ #
    #  Write (tracking propagation/sync)                                  #
    # ------------------------------------------------------------------ #

    def write(self, vals):
        res = super().write(vals)

        if not self.env.context.get('skip_picking_propagation'):
            self._propagate_to_moves(vals)

        if not self.env.context.get('skip_intercompany_sync'):
            self._sync_to_linked_receipts(vals)

        return res

    # ------------------------------------------------------------------ #
    #  Intercompany Delivery cancel safeguard (from dekad_intercompany_rules) #
    # ------------------------------------------------------------------ #

    def _get_intercompany_po(self, picking):
        """ Get the linked PO at the buying company for an intercompany Delivery.
            Chain: Delivery → sale_id (SO at company B)
                   → SO.client_order_ref = PO.name (set by inter-company rules)
        """
        if not picking.sale_id or not picking.sale_id.client_order_ref:
            return self.env['purchase.order']
        return self.env['purchase.order'].sudo().search([
            ('name', '=', picking.sale_id.client_order_ref)
        ], limit=1)

    def action_confirm_cancel(self):
        """ Override: when cancelling an intercompany Delivery (outgoing):

            - If the linked Receipt at the buying company is Done:
              BLOCK and ask user to contact buying company first.

            - If the linked Receipt is Ready (assigned):
              Automatically reset to Draft and re-assign for sync.
        """
        # تحقق أولاً قبل أي Cancel
        for picking in self:
            if picking.picking_type_code != 'outgoing':
                continue

            po = self._get_intercompany_po(picking)
            if not po:
                continue

            done_receipts = po.sudo().picking_ids.filtered(
                lambda p: p.picking_type_code == 'incoming'
                and p.state == 'done'
            )
            if done_receipts:
                raise UserError(_(
                    "Cannot cancel this delivery.\n\n"
                    "The following receipt(s) at company '%(company)s' "
                    "have already been validated:\n%(receipts)s\n\n"
                    "Please contact '%(company)s' to cancel their receipt(s) "
                    "first, then try again.",
                    company=po.company_id.name,
                    receipts='\n'.join(f'- {r.name}' for r in done_receipts),
                ))

        # نفذ الـ Cancel الأصلي
        res = super().action_confirm_cancel()

        # بعد Cancel، عالج الـ assigned receipts
        for picking in self:
            if picking.picking_type_code != 'outgoing':
                continue

            po = self._get_intercompany_po(picking)
            if not po:
                continue

            assigned_receipts = po.sudo().picking_ids.filtered(
                lambda p: p.picking_type_code == 'incoming'
                and p.state == 'assigned'
            )
            if not assigned_receipts:
                continue

            _logger.info(
                "Intercompany: resetting receipts %s to draft because delivery %s was cancelled",
                assigned_receipts.mapped('name'),
                picking.name,
            )

            ctx = dict(self.env.context, mail_notrack=True, tracking_disable=True)
            wizard = self.env['dekad.picking.cancel.wizard'].with_context(ctx).sudo().create({
                'picking_ids': [(6, 0, assigned_receipts.ids)],
                'option': 'cancel_draft',
            })
            wizard.with_context(ctx).action_apply()

            for receipt in assigned_receipts.sudo():
                try:
                    receipt.action_confirm()
                    receipt.action_assign()
                    for move in receipt.move_ids:
                        move.sudo().write({
                            'quantity': 0,
                            'picked': False,
                        })
                except Exception as e:
                    _logger.warning(
                        "Failed to re-assign receipt %s: %s",
                        receipt.name, e
                    )

            for receipt in assigned_receipts:
                receipt.message_post(
                    body=_(
                        "Reset to Draft automatically because the linked "
                        "delivery %(delivery)s in %(company)s was cancelled.",
                        delivery=picking.name,
                        company=picking.company_id.name,
                    )
                )

        return res