from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # =========================================================
    # FIELDS
    # =========================================================

    invoice_delivery_ids = fields.One2many(
        comodel_name='stock.picking',
        inverse_name='source_invoice_id',
        string='Delivery Orders',
        readonly=True,
    )

    invoice_delivery_count = fields.Integer(
        string='Delivery Count',
        compute='_compute_invoice_delivery_count',
    )

    # =========================================================
    # COMPUTE
    # =========================================================

    @api.depends('invoice_delivery_ids')
    def _compute_invoice_delivery_count(self):
        for invoice in self:
            invoice.invoice_delivery_count = len(
                invoice.invoice_delivery_ids
            )

    # =========================================================
    # POST INVOICE
    # =========================================================

    def action_post(self):
        """
        Post customer invoice.

        If no delivery exists:
            create one.

        If a non-done delivery already exists:
            synchronize it with the invoice.
        """
        res = super().action_post()

        for invoice in self:

            if invoice.move_type != 'out_invoice':
                continue

            active_pickings = invoice.invoice_delivery_ids.filtered(
                lambda picking: picking.state != 'cancel'
            )

            if active_pickings:
                invoice._sync_delivery_from_invoice()
            else:
                invoice._create_delivery_from_invoice()

        return res

    # =========================================================
    # RESET TO DRAFT
    # =========================================================

    def button_draft(self):
        """
        Do not allow resetting the invoice to draft when its
        delivery has already been validated.
        """
        for invoice in self:

            if invoice.move_type != 'out_invoice':
                continue

            done_pickings = invoice.invoice_delivery_ids.filtered(
                lambda picking: picking.state == 'done'
            )

            if done_pickings:
                raise UserError(
                    _(
                        'You cannot reset invoice "%(invoice)s" to draft '
                        'because the following delivery order has already '
                        'been validated: %(delivery)s'
                    ) % {
                        'invoice': invoice.display_name,
                        'delivery': ', '.join(
                            done_pickings.mapped('name')
                        ),
                    }
                )

        return super().button_draft()

    # =========================================================
    # GET DELIVERABLE INVOICE LINES
    # =========================================================

    def _get_invoice_deliverable_lines(self):
        """
        Get invoice lines that must appear in the delivery.

        Services are ignored because they do not create
        stock movements.
        """
        self.ensure_one()

        return self.invoice_line_ids.filtered(
            lambda line:
                line.display_type == 'product'
                and line.product_id
                and line.quantity > 0
                and line.product_id.type != 'service'
        )

    # =========================================================
    # GET WAREHOUSE / LOCATIONS
    # =========================================================

    def _get_invoice_delivery_locations(self):
        """
        Automatically use the first warehouse belonging to
        the invoice company.
        """
        self.ensure_one()

        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id),
        ], limit=1)

        if not warehouse:
            raise UserError(
                _(
                    'No warehouse was found for company "%s".'
                ) % self.company_id.display_name
            )

        picking_type = warehouse.out_type_id

        if not picking_type:
            raise UserError(
                _(
                    'No Delivery Orders operation type was found '
                    'for warehouse "%s".'
                ) % warehouse.display_name
            )

        source_location = (
            picking_type.default_location_src_id
            or warehouse.lot_stock_id
        )

        destination_location = (
            self.partner_id.property_stock_customer
        )

        if not source_location:
            raise UserError(
                _(
                    'Could not determine the source stock location '
                    'for warehouse "%s".'
                ) % warehouse.display_name
            )

        if not destination_location:
            raise UserError(
                _(
                    'Could not determine the customer destination '
                    'location for "%s".'
                ) % self.partner_id.display_name
            )

        return (
            warehouse,
            picking_type,
            source_location,
            destination_location,
        )

    # =========================================================
    # PREPARE STOCK MOVE VALUES
    # =========================================================

    def _prepare_invoice_delivery_move_vals(
        self,
        invoice_line,
        picking,
        source_location,
        destination_location,
    ):
        """
        Prepare one stock.move from exactly one invoice line.

        Invoice:
            Product
            Quantity
            UoM
            Description

        are copied to the delivery move.
        """
        self.ensure_one()

        product = invoice_line.product_id

        invoice_uom = (
            invoice_line.product_uom_id
            or product.uom_id
        )

        return {
            'name': (
                invoice_line.name
                or product.display_name
            ),

            'product_id': product.id,

            # Keep the same quantity shown on the invoice.
            'product_uom_qty': invoice_line.quantity,

            # Keep the same UoM shown on the invoice.
            'product_uom': invoice_uom.id,

            'location_id': source_location.id,
            'location_dest_id': destination_location.id,

            'picking_id': picking.id,

            'company_id': self.company_id.id,

            # Direct link:
            # Invoice Line <-> Stock Move
            'source_invoice_line_id': invoice_line.id,
        }

    # =========================================================
    # CREATE DELIVERY
    # =========================================================

    def _create_delivery_from_invoice(self):
        self.ensure_one()

        # -----------------------------------------------------
        # Basic checks
        # -----------------------------------------------------

        if self.move_type != 'out_invoice':
            return False

        if self.state != 'posted':
            return False

        # -----------------------------------------------------
        # Prevent duplicate deliveries
        # -----------------------------------------------------

        existing_picking = self.env['stock.picking'].search([
            ('source_invoice_id', '=', self.id),
            ('state', '!=', 'cancel'),
        ], limit=1)

        if existing_picking:
            return existing_picking

        # -----------------------------------------------------
        # Customer
        # -----------------------------------------------------

        if not self.partner_id:
            raise UserError(
                _('Please select a customer before posting the invoice.')
            )

        # -----------------------------------------------------
        # Invoice lines
        # -----------------------------------------------------

        invoice_lines = self._get_invoice_deliverable_lines()

        # Invoice contains only services.
        if not invoice_lines:
            return False

        # -----------------------------------------------------
        # Warehouse / locations
        # -----------------------------------------------------

        (
            warehouse,
            picking_type,
            source_location,
            destination_location,
        ) = self._get_invoice_delivery_locations()

        # -----------------------------------------------------
        # Create delivery
        # -----------------------------------------------------

        picking = self.env['stock.picking'].create({
            'partner_id': self.partner_id.id,

            'picking_type_id': picking_type.id,

            'location_id': source_location.id,
            'location_dest_id': destination_location.id,

            # stock.picking.move_type
            # NOT account.move.move_type
            'move_type': 'direct',

            'origin': self.name,

            'company_id': self.company_id.id,

            'source_invoice_id': self.id,
        })

        # -----------------------------------------------------
        # Create one move for every invoice line
        # -----------------------------------------------------

        StockMove = self.env['stock.move']

        for invoice_line in invoice_lines:

            move_vals = (
                self._prepare_invoice_delivery_move_vals(
                    invoice_line=invoice_line,
                    picking=picking,
                    source_location=source_location,
                    destination_location=destination_location,
                )
            )

            StockMove.create(move_vals)

        # -----------------------------------------------------
        # Protect against empty picking
        # -----------------------------------------------------

        if not picking.move_ids:
            picking.unlink()
            return False

        # -----------------------------------------------------
        # Confirm
        # -----------------------------------------------------

        picking.action_confirm()

        # -----------------------------------------------------
        # Reserve stock
        # -----------------------------------------------------

        picking.action_assign()

        return picking

    # =========================================================
    # SYNCHRONIZE EXISTING DELIVERY
    # =========================================================

    def _sync_delivery_from_invoice(self):
        """
        Synchronize an existing non-validated delivery with
        the current invoice.

        The invoice is the source of truth.

        Supported changes:

            Product changed
            Quantity changed
            UoM changed
            Description changed
            Line added
            Line removed
            Customer changed

        A DONE delivery is never modified.
        """
        self.ensure_one()

        # -----------------------------------------------------
        # Find active delivery
        # -----------------------------------------------------

        pickings = self.invoice_delivery_ids.filtered(
            lambda picking: picking.state != 'cancel'
        )

        if not pickings:
            return self._create_delivery_from_invoice()

        picking = pickings[0]

        # -----------------------------------------------------
        # Never modify validated delivery
        # -----------------------------------------------------

        if picking.state == 'done':
            raise UserError(
                _(
                    'Delivery order "%s" has already been validated. '
                    'The invoice can no longer modify this delivery.'
                ) % picking.name
            )

        # -----------------------------------------------------
        # Customer
        # -----------------------------------------------------

        if not self.partner_id:
            raise UserError(
                _('Please select a customer.')
            )

        # -----------------------------------------------------
        # Current invoice lines
        # -----------------------------------------------------

        invoice_lines = self._get_invoice_deliverable_lines()

        # -----------------------------------------------------
        # Locations
        # -----------------------------------------------------

        (
            warehouse,
            picking_type,
            source_location,
            destination_location,
        ) = self._get_invoice_delivery_locations()

        # -----------------------------------------------------
        # Unreserve existing stock
        # -----------------------------------------------------

        if picking.state in ('assigned', 'partially_available'):
            picking.do_unreserve()

        # -----------------------------------------------------
        # Update delivery header
        # -----------------------------------------------------

        picking.write({
            'partner_id': self.partner_id.id,
            'location_id': source_location.id,
            'location_dest_id': destination_location.id,
            'origin': self.name,
        })

        # -----------------------------------------------------
        # Existing stock moves
        # -----------------------------------------------------

        existing_moves = picking.move_ids.filtered(
            lambda move: move.state != 'done'
        )

        # -----------------------------------------------------
        # Remove moves for deleted invoice lines
        # -----------------------------------------------------

        invoice_line_ids = set(invoice_lines.ids)

        obsolete_moves = existing_moves.filtered(
            lambda move:
                not move.source_invoice_line_id
                or move.source_invoice_line_id.id
                not in invoice_line_ids
        )

        if obsolete_moves:

            moves_to_cancel = obsolete_moves.filtered(
                lambda move: move.state not in (
                    'draft',
                    'cancel',
                )
            )

            if moves_to_cancel:
                moves_to_cancel._action_cancel()

            obsolete_moves.unlink()

        # -----------------------------------------------------
        # Synchronize every invoice line
        # -----------------------------------------------------

        StockMove = self.env['stock.move']

        for invoice_line in invoice_lines:

            existing_move = picking.move_ids.filtered(
                lambda move:
                    move.state != 'done'
                    and move.source_invoice_line_id == invoice_line
            )[:1]

            move_vals = (
                self._prepare_invoice_delivery_move_vals(
                    invoice_line=invoice_line,
                    picking=picking,
                    source_location=source_location,
                    destination_location=destination_location,
                )
            )

            if existing_move:

                # Fields that cannot/should not be rewritten.
                move_vals.pop('picking_id', None)
                move_vals.pop('company_id', None)

                existing_move.write(move_vals)

            else:

                StockMove.create(move_vals)

        # -----------------------------------------------------
        # Confirm draft moves
        # -----------------------------------------------------

        draft_moves = picking.move_ids.filtered(
            lambda move: move.state == 'draft'
        )

        if draft_moves:
            draft_moves._action_confirm()

        # -----------------------------------------------------
        # Reserve current quantities
        # -----------------------------------------------------

        if picking.move_ids.filtered(
            lambda move: move.state not in ('done', 'cancel')
        ):
            picking.action_assign()

        return picking

    # =========================================================
    # DELIVERY SMART BUTTON
    # =========================================================

    def action_view_invoice_deliveries(self):
        self.ensure_one()

        pickings = self.invoice_delivery_ids

        if not pickings:
            return False

        action = self.env[
            'ir.actions.actions'
        ]._for_xml_id(
            'stock.action_picking_tree_all'
        )

        if len(pickings) == 1:

            action.update({
                'views': [
                    (
                        self.env.ref(
                            'stock.view_picking_form'
                        ).id,
                        'form',
                    )
                ],
                'res_id': pickings.id,
                'domain': [],
            })

        else:

            action.update({
                'domain': [
                    ('id', 'in', pickings.ids),
                ],
            })

        action['context'] = {
            'create': False,
        }

        return action