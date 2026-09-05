from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta, date
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import formatLang

import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    rent_start_date = fields.Date(
        string='Rent Start Date',
    )

    rent_end_date = fields.Date(
        string='Rent End Date',
    )

    rent_state = fields.Selection([
        ('not_booked', "Not Booked"),
        ('booked', "Booked"),
        ('not_paid', "Not Paid"),
        ('partially_paid', "Partially Paid"),
        ('paid', "Paid"),
        ('cancel', "Cancelled")
    ], readonly=True, default="not_booked", compute="_compute_rent_state", store=True)

    related_buildings_ids = fields.Many2one(
        comodel_name='real.estate.buildings',
        string='Building',
        related='account_analytic_account_id.property_building_id',
        store=True,
        readonly=True,
        copy=False,
        ondelete='set null'
    )

    property_building_id = fields.Many2one(
        comodel_name='real.estate.buildings',
        string='Building',
        store=True,
    )

    so_meter_reading_ids = fields.One2many(
        comodel_name='meter.reading',
        inverse_name='sale_order_id',
        string='Meter Readings',
        store=True,
    )

    guarant_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Guarant',
        store=True,
        copy=True,
        ondelete='set null'
    )

    account_analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Property',
        ondelete='set null',
        copy=True,
        store=True,
    )

    cancel_type = fields.Selection([
        ('paid_cancel', 'Cancel & Refund'),
        ('free_cancel', 'No Response'),
        ('no_show', 'Cancel without Refund'),
        ('early_checkout', 'Early Checkout'),
    ], string="Cancellation Type", readonly=True, copy=False, store=True)

    cancel_reason = fields.Text(string="Cancellation Reason", readonly=True, copy=False)

    show_cancel_info = fields.Boolean(compute="_compute_show_cancel_info", readonly=True, store=False)
    checkout_date = fields.Date(string="Early Checkout Date", readonly=True, copy=False)

    def _compute_show_cancel_info(self):
        for order in self:
            order.show_cancel_info = (
                    self.env.context.get('rental_mode') and order.state == 'cancel'
            )

    rental_mode = fields.Boolean(string="Rental Mode", compute='_compute_rental_mode', store=False)

    rental_type = fields.Selection([
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),

    ], string='Rental Type', default='daily', required=True, store=True)

    hour_number = fields.Float(
        string='Number of Hours',
        help='Total rental hours (only for hourly rentals)'
    )

    linked_product_ids = fields.Many2many(
        'product.product',
        string='Linked Products',
        compute='_compute_linked_products',
        store=False,
    )

    payment_id = fields.Many2one('account.payment', string="Receipt Voucher Payment", readonly=True)

    @api.depends(
        'state',
        'payment_id.state',
        'cancel_type',
        'rental_type',
        'invoice_ids.state',
        'invoice_ids.payment_state',
        'invoice_ids.pdc_payment_ids.state'
    )
    def _compute_rent_state(self):
        for rec in self:
            # Handle cancellations first
            if rec.state == 'cancel':
                if rec.cancel_type == 'free_cancel' and rec.rent_state == 'booked':
                    rec.rent_state = 'not_booked'
                elif rec.cancel_type == 'paid_cancel':
                    rec.rent_state = 'cancel'
                continue

            # Default
            rec.rent_state = 'not_booked'

            # If confirmed order
            if rec.state == 'sale':
                rec.rent_state = 'booked'

                # ==========================================
                # YEARLY RENTAL SPECIAL LOGIC (PDC BASED)
                # ==========================================
                if rec.rental_type in ['yearly', 'monthly']:

                    posted_invoices = rec.invoice_ids.filtered(
                        lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
                    )

                    if posted_invoices:

                        # 1. Accounting payments
                        total_invoice_paid = sum(
                            inv.amount_total - inv.amount_residual
                            for inv in posted_invoices
                        )

                        # 2. PDC (only deposited & NOT yet reconciled)
                        all_pdcs = posted_invoices.mapped('pdc_payment_ids')
                        deposited_pdcs = all_pdcs.filtered(lambda p: p.state == 'deposited')

                        total_pdc_amount = sum(deposited_pdcs.mapped('payment_amount'))

                        #  Adjust here if PDC is later reconciled (important)
                        total_paid = total_invoice_paid + total_pdc_amount

                        if total_paid >= rec.amount_total:
                            rec.rent_state = 'paid'
                        elif total_paid > 0:
                            rec.rent_state = 'partially_paid'
                        else:
                            rec.rent_state = 'booked'

                    continue

                posted_invoices = rec.invoice_ids.filtered(
                    lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
                )
                if posted_invoices:
                    payment_states = posted_invoices.mapped('payment_state')
                    if all(ps == 'paid' for ps in payment_states):
                        rec.rent_state = 'paid'
                    elif any(ps == 'partial' for ps in payment_states):  # ← NEW
                        rec.rent_state = 'partially_paid'
                elif rec.payment_id and rec.payment_id.state == 'paid':
                    rec.rent_state = 'paid'



    @api.depends_context('rental_mode')
    def _compute_rental_mode(self):
        for order in self:
            order.rental_mode = self.env.context.get('rental_mode', False)

    def _update_rental_contract_on_property(self):
        for order in self:
            property = order.account_analytic_account_id
            if property and property.is_property:
                active_contracts = property.rental_contract_id.filtered(lambda c: c.state == 'sale')

                if not active_contracts:
                    _logger.info(f"No active contract for property '{property.name}', this one will be tracked.")




    def action_open_receipt_voucher(self):
        self.ensure_one()

        # Check for existing draft payment linked to this sale order
        existing_payment = self.env['account.payment'].search([
            ('sale_order_id', '=', self.id),
            ('state', '=', 'draft')
        ], limit=1)

        if existing_payment:
            # Open the existing draft payment
            return {
                'name': 'Receipt Voucher',
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'view_mode': 'form',
                'res_id': existing_payment.id,
                'target': 'new',
            }

        # Otherwise, create a new one
        return {
            'name': 'Receipt Voucher',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_amount': self.amount_total,
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_communication': self.name,
                'default_currency_id': self.currency_id.id,
                'hide_payment_journal_id': True,
                'default_sale_order_id': self.id,
            }
        }

    def action_open_linked_payment(self):
        self.ensure_one()

        payments = self.env['account.payment']

        # Direct payment
        if self.payment_id:
            payments |= self.payment_id

        # Payments from invoices
        invoice_payments = self.invoice_ids.mapped(
            'line_ids.matched_debit_ids.debit_move_id.payment_id'
        ) | self.invoice_ids.mapped(
            'line_ids.matched_credit_ids.credit_move_id.payment_id'
        )

        payments |= invoice_payments

        payments = payments.filtered(lambda p: p)

        if not payments:
            return False

        return {
            'name': 'Payments',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', payments.ids)],
            'target': 'current',
        }

    @api.model
    def _cron_check_contract_due_status(self):
        """CRON: Change state to 'not_paid' if rent_end_date <= today and still in 'sale'."""
        today = date.today()
        orders_to_update = self.search([
            ('rent_state', '=', 'booked'),
            ('rent_end_date', '!=', False),
            ('rent_end_date', '=', today),
        ])
        for order in orders_to_update:
            order.rent_state = 'not_paid'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        today = date.today()

        # Default Start Date
        if 'rent_start_date' in fields_list:
            res['rent_start_date'] = today

        # Determine rental type (from context or default)
        rental_type = res.get('rental_type') or self._fields['rental_type'].default(self)

        # Default End Date based on rental type
        if 'rent_end_date' in fields_list:
            if rental_type == 'monthly':
                res['rent_end_date'] = today + relativedelta(months=1)
            elif rental_type == 'yearly':
                res['rent_end_date'] = today + relativedelta(years=1)
            else:  # daily or hourly
                res['rent_end_date'] = today + relativedelta(days=1)

        return res

    @api.onchange('rental_type', 'rent_start_date')
    def _onchange_rental_type_dates(self):
        if not self.rent_start_date:
            return

        if self.rental_type == 'monthly':
            self.rent_end_date = (
                                         self.rent_start_date + relativedelta(months=1)
                                 ) - timedelta(days=1)

        elif self.rental_type == 'yearly':
            self.rent_end_date = (
                                         self.rent_start_date + relativedelta(years=1)
                                 ) - timedelta(days=1)
        else:
            self.rent_end_date = self.rent_start_date + relativedelta(days=1)


    @api.onchange('account_analytic_account_id', 'rent_start_date', 'rent_end_date','rental_type')
    def _onchange_account_analytic_account_id_create_lines(self):
        property = self.account_analytic_account_id
        if not property or not self.rent_start_date or not self.rent_end_date:
            return

        self.order_line = [(5, 0, 0)]  # Clear old lines
        lines = []

        # MONTHLY / YEARLY → ONLY ONE LINE PER PRODUCT
        if self.rental_type in ['monthly', 'yearly']:
            for product in property.product_ids:
                lines.append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'price_unit': product.lst_price,
                    'name': f"{product.name} "
                            f"({self.rental_type.capitalize()} Rental "
                            f"{self.rent_start_date} - {self.rent_end_date})",
                }))

            self.order_line = lines
            return


        # 1. Covered dates by rental events
        covered_product_dates = set()  # Set of (product_id, date) already billed by event
        rental_events = property.rental_event_ids.filtered(
            lambda ev: ev.start_date < self.rent_end_date and ev.end_date >= self.rent_start_date
        )

        for event in rental_events:
            # Get range and exclude rent_end_date
            event_dates = self._get_date_range(event.start_date, event.end_date)
            event_dates = [d for d in event_dates if d < self.rent_end_date]

            for product in property.product_ids:
                for ev_date in event_dates:
                    covered_product_dates.add((product.id, ev_date))

            for product in property.product_ids:
                lines.append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'price_unit': event.cost or 0,
                    'name': event.description or f"{product.name} ({event.start_date})",
                }))

        # 2. Default price lines for uncovered dates only
        all_dates = self._get_date_range(self.rent_start_date, self.rent_end_date)
        all_dates = [d for d in all_dates if d < self.rent_end_date]

        for single_date in all_dates:
            for product in property.product_ids:
                if (product.id, single_date) in covered_product_dates:
                    continue  # Skip duplicates

                lines.append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'price_unit': product.lst_price,
                    'name': f"{product.name} (Default Price for {single_date})",
                }))

        self.order_line = lines

    def _get_date_range(self, start_date, end_date):
        return [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    @api.constrains('account_analytic_account_id', 'rent_start_date', 'rent_end_date')
    def check_rental_overlap(self):
        for order in self:
            if not order.account_analytic_account_id or not order.rent_start_date or not order.rent_end_date:
                continue

            if order.state == 'cancel':
                continue

            # Exclude the current order's end date from the comparison
            current_start = order.rent_start_date
            current_end_exclusive = order.rent_end_date

            candidate_orders = self.env['sale.order'].search([
                ('id', '!=', order.id),
                ('account_analytic_account_id', '=', order.account_analytic_account_id.id),
                ('state', '!=', 'cancel'),
                ('rent_state', '!=', 'not_booked'), ])

            # Filter real conflicts: start < other_end AND end > other_start
            conflicting_orders = candidate_orders.filtered(lambda o:
                                                           o.rent_start_date and o.rent_end_date and
                                                           o.rent_start_date < current_end_exclusive and
                                                           o.rent_end_date > current_start
                                                           )

            if conflicting_orders:
                conflict_names = ', '.join(conflicting_orders.mapped('name'))
                raise ValidationError(
                    f"The property '{order.account_analytic_account_id.name}' "
                    f"is already rented in this period. Conflicts with: {conflict_names}"
                )

    bedroom_no = fields.Integer(
        string='Bedroom No',
        related='account_analytic_account_id.bedroom_no',
        store=True,
        readonly=True
    )

    bedroom_label = fields.Char(
        string='Bedroom Label',
        compute='_compute_bedroom_label',
        store=True
    )

    @api.depends('bedroom_no')
    def _compute_bedroom_label(self):
        for rec in self:
            if rec.bedroom_no:
                rec.bedroom_label = f"{rec.bedroom_no} Bedroom"
            else:
                rec.bedroom_label = "No Bedroom"


    @api.model
    def create(self, vals):
        order = super().create(vals)

        # Set contract on property
        order._update_rental_contract_on_property()

        return order


    def write(self, vals):
        res = super().write(vals)

        # Set contract on property
        self._update_rental_contract_on_property()

        return res

    @api.depends('name')
    def _compute_display_name(self):
        for order in self:
            order.display_name = order.name

    @api.constrains('rent_start_date', 'rent_end_date')
    def _check_rent_dates(self):
        for order in self:
            today = date.today()


            if order.rent_start_date and order.rent_end_date:
                if order.rent_end_date < order.rent_start_date:
                    raise ValidationError("Rent end date must be on or after the start date.")

    @api.onchange('rent_start_date', 'rent_end_date')
    def _onchange_rent_dates(self):
        today = date.today()


        if self.rent_start_date and self.rent_end_date and self.rent_end_date < self.rent_start_date:
            return {
                'warning': {
                    'title': "Invalid End Date",
                    'message': "End date must be on or after the start date.",
                }
            }

    @api.onchange('property_building_id')
    def _onchange_property_building_id(self):
        domain = [('is_property', '=', True), ('offer_type', '=', 'rent')]
        if self.property_building_id:
            domain.append(('property_building_id', '=', self.property_building_id.id))
        return {'domain': {'account_analytic_account_id': domain}}

    @api.onchange('account_analytic_account_id')
    def _onchange_account_analytic_account_id_set_building(self):
        if self.account_analytic_account_id:
            self.property_building_id = self.account_analytic_account_id.property_building_id

    def action_confirm(self):
        for order in self:
            order.check_rental_overlap()
            if not order.order_line:
                raise UserError("You cannot confirm a contract without items.")
        return super(SaleOrder, self).action_confirm()

    number_of_nights = fields.Integer(
        string='Number of Nights',
        compute='_compute_number_of_nights',
        store=True,
        readonly=True
    )

    @api.depends('rent_start_date', 'rent_end_date', 'rental_type')
    def _compute_number_of_nights(self):
        for order in self:
            if order.rent_start_date and order.rent_end_date:
                delta = (order.rent_end_date - order.rent_start_date).days

                # Add 1 extra day for yearly
                if order.rental_type in ['yearly']:
                    delta += 1

                order.number_of_nights = max(delta, 0)
            else:
                order.number_of_nights = 0

    def open_cancel_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cancel Options',
            'res_model': 'rental.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
        }


    municipality_contract_number = fields.Char(
        string='رقم عقد البلدية',
        copy=False,
    )

    is_rental_contract = fields.Boolean(string="Is Rental Contract", default=False, readonly=True)
    sale_mode = fields.Boolean(string="Sale Mode", compute='_compute_sale_mode', store=False)
    is_property_sale_contract = fields.Boolean(
        string="Is Property Sale Contract",
        default=False,
        readonly=True
    )
    is_property_sold = fields.Boolean(
        string="Sold",
        compute='_compute_is_property_sold',
        store=True,
        readonly=True
    )

    @api.depends('invoice_ids.state', 'is_property_sale_contract')
    def _compute_is_property_sold(self):
        for order in self:
            if not order.is_property_sale_contract:
                order.is_property_sold = False
                continue

            posted_invoice_exists = order.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
            )

            order.is_property_sold = bool(posted_invoice_exists)

    @api.depends_context('sale_mode')
    def _compute_sale_mode(self):
        for order in self:
            order.sale_mode = self.env.context.get('sale_mode', False)

    payment_method_ids = fields.Many2many(
        comodel_name='account.payment.method.line',
        string='Payment Methods',
        compute='_compute_payment_method_ids',
        store=True,
    )

    @api.depends(
        'invoice_ids.state',
        'invoice_ids.payment_state',
        'invoice_ids.line_ids.matched_debit_ids.debit_move_id.payment_id.payment_method_line_id',
        'invoice_ids.line_ids.matched_credit_ids.credit_move_id.payment_id.payment_method_line_id',
        'invoice_ids.pdc_payment_ids.state',
        'payment_id.payment_method_line_id',
    )
    def _compute_payment_method_ids(self):
        for order in self:
            methods = self.env['account.payment.method.line']

            invoices = order.invoice_ids.filtered(
                lambda inv: inv.state == 'posted'
                            and inv.move_type in ('out_invoice', 'out_refund')
            )

            # ✅ ONLY real payments (exclude PDC)
            payments = invoices.mapped(
                'line_ids.matched_debit_ids.debit_move_id.payment_id'
            ) | invoices.mapped(
                'line_ids.matched_credit_ids.credit_move_id.payment_id'
            )

            methods |= payments.mapped('payment_method_line_id')

            # ✅ Direct payment (non-PDC)
            if order.payment_id and order.payment_id.payment_method_line_id:
                methods |= order.payment_id.payment_method_line_id

            order.payment_method_ids = methods



    payment_info_ids = fields.One2many(
        'sale.order.payment.info',
        'sale_order_id',
        string="Payment Details",
        compute='_compute_payment_info',
        store=True,
    )

    @api.depends(
        'invoice_ids.state',
        'invoice_ids.payment_state',
        'invoice_ids.line_ids.matched_debit_ids.debit_move_id.payment_id',
        'invoice_ids.line_ids.matched_credit_ids.credit_move_id.payment_id',
        'invoice_ids.line_ids.matched_debit_ids.debit_move_id.payment_id.payment_method_line_id',
        'invoice_ids.line_ids.matched_credit_ids.credit_move_id.payment_id.payment_method_line_id',
        'invoice_ids.line_ids.matched_debit_ids.debit_move_id.payment_id.amount',
        'invoice_ids.line_ids.matched_credit_ids.credit_move_id.payment_id.amount',
        'payment_id.amount',
        'payment_id.state',
        'payment_id.payment_method_line_id',
    )
    def _compute_payment_info(self):
        for order in self:
            lines = []

            invoices = order.invoice_ids.filtered(
                lambda inv: inv.state == 'posted'
                            and inv.move_type in ('out_invoice', 'out_refund')
            )

            # ==========================================
            # 1. INVOICE PAYMENTS ONLY
            # ==========================================
            payments = invoices.mapped(
                'line_ids.matched_debit_ids.debit_move_id.payment_id'
            ) | invoices.mapped(
                'line_ids.matched_credit_ids.credit_move_id.payment_id'
            )

            for pay in payments:
                if not pay.payment_method_line_id:
                    continue

                lines.append((0, 0, {
                    'payment_method_line_id': pay.payment_method_line_id.id,
                    'amount': pay.amount,
                    'source': 'invoice',
                }))

            # ==========================================
            # 2. DIRECT PAYMENT (ONLY IF NOT IN INVOICES)
            # ==========================================
            if order.payment_id and order.payment_id not in payments:
                if order.payment_id.payment_method_line_id:
                    lines.append((0, 0, {
                        'payment_method_line_id': order.payment_id.payment_method_line_id.id,
                        'amount': order.payment_id.amount,
                        'source': 'direct',
                    }))

            # ==========================================
            # FINAL WRITE
            # ==========================================
            order.payment_info_ids = [(5, 0, 0)] + lines


    payment_info_tag_ids = fields.Many2many(
        'sale.order.payment.info',
        compute='_compute_payment_info_tags',
        string="Payments",
        store=False
    )

    @api.model
    def action_recompute_payment_info(self):
        """Backfill payment_info_ids on existing orders."""
        orders = self.search([
            ('state', 'in', ['sale', 'cancel']),
            ('invoice_ids', '!=', False),
        ])

        # optional cleanup to avoid duplicates
        self.env['sale.order.payment.info'].search([
            ('sale_order_id', 'in', orders.ids)
        ]).unlink()

        orders._compute_payment_info()
        return True


    def _compute_payment_info_tags(self):
        for order in self:
            order.payment_info_tag_ids = order.payment_info_ids

    # ==========================================================
    # BUILDING STATEMENT
    # One row per (non-draft) normal payment or PDC that is
    # reconciled against a posted invoice on this order.
    # ==========================================================

    building_statement_line_ids = fields.One2many(
        'building.statement.line',
        'sale_order_id',
        string="Building Statement Lines",
        compute='_compute_building_statement_lines',
        store=True,
    )

    @api.depends(
        'partner_id',
        'rent_end_date',
        'rent_start_date',
        'property_building_id',
        'related_buildings_ids',
        'account_analytic_account_id',
        'invoice_ids.state',
        'invoice_ids.line_ids.matched_debit_ids.debit_move_id.payment_id',
        'invoice_ids.line_ids.matched_credit_ids.credit_move_id.payment_id',
        'invoice_ids.line_ids.matched_debit_ids.debit_move_id.payment_id.state',
        'invoice_ids.line_ids.matched_credit_ids.credit_move_id.payment_id.state',
        'invoice_ids.line_ids.matched_debit_ids.debit_move_id.payment_id.amount',
        'invoice_ids.line_ids.matched_credit_ids.credit_move_id.payment_id.amount',
        'invoice_ids.line_ids.matched_debit_ids.debit_move_id.payment_id.date',
        'invoice_ids.line_ids.matched_credit_ids.credit_move_id.payment_id.date',
        'invoice_ids.pdc_payment_ids.state',
        'invoice_ids.pdc_payment_ids.payment_amount',
        'invoice_ids.pdc_payment_ids.due_date',
    )
    def _compute_building_statement_lines(self):
        for order in self:
            building = order.property_building_id or order.related_buildings_ids
            property_rec = order.account_analytic_account_id

            posted_invoices = order.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
            )

            if not posted_invoices:
                order.building_statement_line_ids = [(5, 0, 0)]
                continue

            lines_vals = []

            # --------------------------------------------------
            # 1. NORMAL PAYMENTS (anything that isn't a PDC) —
            #    not draft, reconciled against a posted invoice
            #    on this SO.
            # --------------------------------------------------
            payments = posted_invoices.mapped(
                'line_ids.matched_debit_ids.debit_move_id.payment_id'
            ) | posted_invoices.mapped(
                'line_ids.matched_credit_ids.credit_move_id.payment_id'
            )
            # payments = payments.filtered(lambda p: p.state != 'draft')

            for pay in payments:
                lines_vals.append((0, 0, {
                    'building_id': building.id if building else False,
                    'property_id': property_rec.id if property_rec else False,
                    'contract_number': order.name,
                    'customer_id': order.partner_id.id,
                    'rent_end_date': order.rent_end_date,
                    'rent_start_date': order.rent_start_date,
                    'payment_type': 'payment',
                    'memo': pay.name or False,
                    'payment_date': pay.date,
                    'amount': pay.amount,
                    'payment_state': 'collected' if pay.state == 'paid' else 'not_collected',

                }))

            # --------------------------------------------------
            # 2. PDC — not draft, linked to a posted invoice
            #    on this SO.
            # --------------------------------------------------
            pdcs = posted_invoices.mapped('pdc_payment_ids').filtered(
                lambda p: p.state != 'draft'
            )

            for pdc in pdcs:
                lines_vals.append((0, 0, {
                    'building_id': building.id if building else False,
                    'property_id': property_rec.id if property_rec else False,
                    'contract_number': order.name,
                    'customer_id': order.partner_id.id,
                    'rent_end_date': order.rent_end_date,
                    'rent_start_date': order.rent_start_date,
                    'payment_type': 'pdc',
                    'memo': getattr(pdc, 'name', False) or False,
                    'payment_date': pdc.due_date,
                    'amount': pdc.payment_amount,
                    'payment_state': 'collected' if pdc.state == 'done' else 'not_collected',
                }))

            order.building_statement_line_ids = [(5, 0, 0)] + lines_vals


    @api.model
    def action_recompute_building_statement(self):
        orders = self.search([
            ("is_rental_contract", "=", True),
        ])

        lines = self.env["building.statement.line"].search([
            ("sale_order_id", "in", orders.ids),
        ])
        lines.unlink()
        self.env.cr.commit()

        batch_size = 50
        total = len(orders)

        for i in range(0, total, batch_size):
            batch = orders[i:i + batch_size]
            batch.invalidate_recordset()
            batch._compute_building_statement_lines()
            self.env.cr.commit()

        return True


    renewal_parent_id = fields.Many2one(
        'sale.order', string='Renewed From', copy=False, readonly=True, index=True,
        help="The original rental contract this order was created to renew.")
    renewal_child_id = fields.Many2one(
        'sale.order', string='Renewal Contract', copy=False, readonly=True,
        help="The renewal contract generated from this order, if any.")
    is_renewal = fields.Boolean(compute='_compute_is_renewal', store=True)
    renewal_count = fields.Integer(compute='_compute_renewal_count')

    renewal_status = fields.Selection([
        ('none', ''),
        ('renewal_quotation', 'Draft'),
        ('renewed', 'Renewed'),
    ], string='Renewal Status', compute='_compute_renewal_status', store=True)

    @api.depends('renewal_parent_id', 'renewal_child_id', 'state')
    def _compute_renewal_status(self):
        for order in self:
            if order.renewal_parent_id and order.state in ('draft', 'sent'):
                # This order IS the renewal, still a quotation
                order.renewal_status = 'renewal_quotation'
            elif order.renewal_child_id:
                # This order has already generated a renewal
                order.renewal_status = 'renewed'
            else:
                order.renewal_status = 'none'



    @api.depends('renewal_parent_id')
    def _compute_is_renewal(self):
        for order in self:
            order.is_renewal = bool(order.renewal_parent_id)


    @api.depends('renewal_parent_id', 'renewal_child_id')
    def _compute_renewal_count(self):
        for order in self:
            count = 0
            node = order
            while node.renewal_parent_id:
                count += 1
                node = node.renewal_parent_id
            node = order
            while node.renewal_child_id:
                count += 1
                node = node.renewal_child_id
            order.renewal_count = count

    # ---------------------------------------------------------
    # Renewal actions
    # ---------------------------------------------------------

    def action_renew_order(self):
        """Create (or reopen) a draft renewal contract that starts right
        after this contract's rent_end_date, copying the order lines as-is.
        """
        self.ensure_one()

        if not self.invoice_ids.filtered(lambda inv: inv.state == 'posted'):
            raise UserError(_("You cannot renew a contract that has no posted invoice."))

        if self.renewal_child_id:
            # Already renewed once: just reopen the existing renewal instead
            # of creating a duplicate.
            action = self._get_renewal_form_action()
            action['res_id'] = self.renewal_child_id.id
            return action

        if not self.rent_end_date:
            raise UserError(_("You cannot renew a contract that has no end date."))

        new_start = self.rent_end_date + timedelta(days=1)
        new_end = self._get_renewal_end_date(new_start)

        renewal = self.copy({
            'renewal_parent_id': self.id,
            'renewal_child_id': False,
            'rent_start_date': new_start,
            'rent_end_date': new_end,
            'state': 'draft',
            'rent_state': 'not_booked',
            'cancel_type': False,
            'cancel_reason': False,
            'checkout_date': False,
            'payment_id': False,
        })

        self.renewal_child_id = renewal.id
        renewal.message_post(
            body=_("This contract renews %s.", self._get_html_link()))
        self.message_post(
            body=_("A renewal quotation %s has been created.", renewal._get_html_link()))

        action = self._get_renewal_form_action()
        action['res_id'] = renewal.id
        return action

    def action_open_renewal_chain(self):
        """Show every contract in this renewal chain (ancestors + descendants)."""
        self.ensure_one()
        chain_ids = set(self.ids)

        node = self
        while node.renewal_parent_id:
            node = node.renewal_parent_id
            chain_ids.add(node.id)

        node = self
        while node.renewal_child_id:
            node = node.renewal_child_id
            chain_ids.add(node.id)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal History'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', list(chain_ids))],
            'context': {'create': False},
        }

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _get_renewal_end_date(self, new_start):
        """Compute the renewal's end date using the same duration/logic
        as the original contract's rental_type.
        """
        self.ensure_one()
        if self.rental_type == 'monthly':
            return new_start + relativedelta(months=1) - timedelta(days=1)
        elif self.rental_type == 'yearly':
            return new_start + relativedelta(years=1) - timedelta(days=1)
        elif self.rental_type == 'hourly':
            return new_start
        else:
            # daily (or anything else): keep the same duration in days
            duration_days = (self.rent_end_date - self.rent_start_date).days
            return new_start + timedelta(days=max(duration_days, 1))



    def _get_renewal_form_action(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }


    is_closed = fields.Boolean(default=False, copy=False, readonly=True, store=True)
    close_reason_id = fields.Many2one(
        'rental.close.reason',
        string="Close Reason",
        copy=False,
        readonly=True,
    )
    close_date = fields.Date(string="Close Date", copy=False, readonly=True)

    contract_status = fields.Selection([
        ('in_progress', 'In Progress'),
        ('churned', 'Closed'),
        ('renewed', 'Renewed'),
    ], string='Contract Status', compute='_compute_contract_status', store=True)

    @api.depends('state', 'is_closed', 'renewal_child_id')
    def _compute_contract_status(self):
        for order in self:
            if order.renewal_child_id:
                order.contract_status = 'renewed'
            elif order.is_closed:
                order.contract_status = 'churned'
            elif order.state == 'sale':
                order.contract_status = 'in_progress'
            else:
                order.contract_status = False

    def action_open_close_wizard(self):
        self.ensure_one()
        if self.is_closed:
            raise UserError(_("This contract is already closed."))
        if not self.invoice_ids.filtered(lambda inv: inv.state == 'posted'):
            raise UserError(_("You cannot close a contract that has no posted invoice."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Close Contract'),
            'res_model': 'rental.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_id': self.id},
        }

    def set_close(self, close_reason_id=False):
        for order in self:
            order.write({
                'is_closed': True,
                'close_date': fields.Date.context_today(order),
                'close_reason_id': close_reason_id.id if close_reason_id else False,
            })
            reason_name = close_reason_id.name if close_reason_id else _("Not specified")
            order.message_post(body=_("Contract has been closed. Reason: %s", reason_name))


    def action_reopen_contract(self):
        self.ensure_one()
        if not self.is_closed:
            raise UserError(_("This contract is not closed."))
        self.write({
            'is_closed': False,
            'close_date': False,
            'close_reason_id': False,
        })
        self.message_post(body=_("Contract has been reopened."))


class SaleOrderPaymentInfo(models.Model):
    _name = 'sale.order.payment.info'
    _description = 'Sale Order Payment Details'
    _rec_name = 'name'

    sale_order_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        ondelete='cascade'
    )

    payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string="Payment Method",
        required=True
    )

    amount = fields.Monetary(string="Amount")

    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        store=True
    )

    source = fields.Selection([
        ('invoice', 'Invoice Payment'),
        ('pdc', 'PDC'),
        ('direct', 'Direct Payment'),
    ], string="Source")

    name = fields.Char(compute="_compute_name", store=False)

    @api.depends('payment_method_line_id', 'amount', 'currency_id')
    def _compute_name(self):
        for rec in self:
            base_name = rec.payment_method_line_id.display_name or ''
            amount = formatLang(self.env, rec.amount, currency_obj=rec.currency_id)

            rec.name = f"{base_name} - {amount}"



class RentalCloseWizard(models.TransientModel):
    _name = 'rental.close.wizard'
    _description = 'Close Rental Contract Wizard'

    sale_order_id = fields.Many2one('sale.order', required=True)
    close_reason_id = fields.Many2one(
        'rental.close.reason',
        string="Close Reason",
        required=True,
    )

    def action_confirm_close(self):
        self.ensure_one()
        self.sale_order_id.set_close(self.close_reason_id)
        return {'type': 'ir.actions.act_window_close'}

class RentalCloseReason(models.Model):
    _name = 'rental.close.reason'
    _description = 'Rental Contract Close Reason'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)