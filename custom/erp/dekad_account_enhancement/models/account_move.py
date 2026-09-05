from odoo import models, _, fields
from odoo.exceptions import UserError
import re

CUSTOMER_MOVE_TYPES = ('out_invoice', 'out_refund')

class AccountAccount(models.Model):
    _inherit = "account.account"

    prevent_negative_balance = fields.Boolean(
        string="Prevent Negative Balance"
    )


class AccountMove(models.Model):
    _inherit = 'account.move'


    force_draft_used = fields.Boolean(
        string="Force Reset to Draft Used",
        default=False,
        readonly=True,
        copy=False,
    )

    return_picking_ids = fields.Many2many(
        'stock.picking',
        compute='_compute_return_picking_ids'
    )

    return_picking_count = fields.Integer(
        compute='_compute_return_picking_ids',
        store=False
    )


    def action_open_discount_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Discount',
            'res_model': 'account.invoice.discount',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_id': self.id},
        }


    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        if 'partner_id' not in fields_list or defaults.get('partner_id'):
            return defaults

        # move_type may come from the returned defaults or from the
        # action context (e.g. default_move_type=out_invoice when opening
        # the Customer Invoices menu).
        move_type = defaults.get('move_type') or self._context.get('default_move_type')

        if move_type in CUSTOMER_MOVE_TYPES:
            company_id = defaults.get('company_id') or self.env.company.id
            company = self.env['res.company'].browse(company_id)
            if company.dekad_default_customer_id:
                defaults['partner_id'] = company.dekad_default_customer_id.id

        return defaults

    def button_force_draft(self):
        """Force reset the moves to draft."""
        self.mapped('line_ids.analytic_line_ids').unlink()
        self.mapped('line_ids').remove_move_reconcile()

        # Bypass AccountMove.write()'s guardrails
        super(AccountMove, self).write({
            'state': 'draft',
            'inalterable_hash': False,
            'secure_sequence_number': 0,
        })

        self._detach_attachments()

        # Mark as force reset (only first time)
        moves_to_update = self.filtered(lambda m: not m.force_draft_used)
        if moves_to_update:
            super(AccountMove, moves_to_update).write({
                'force_draft_used': True,
                })



    def action_post(self):

        for move in self:

            # -------------------------------------------------
            # Credit Limit Validation
            # -------------------------------------------------
            if (
                    move.move_type == "out_invoice"
                    and move.partner_id
                    and move.partner_id.show_credit_limit
                    and not self.env.user.has_group(
                "dekad_account_enhancement.group_exceed_credit_limit"
            )
            ):

                # credit + credit_to_invoice + current invoice
                if move.partner_credit_warning:
                    raise UserError(_(
                        "You cannot post this invoice.\n\n%s"
                    ) % move.partner_credit_warning)

            # -------------------------------------------------
            # Prevent Negative Account Balance
            # -------------------------------------------------
            accounts_to_check = move.line_ids.mapped("account_id").filtered(
                lambda a: a.prevent_negative_balance
            )

            for account in accounts_to_check:

                current_balance = account.current_balance

                lines = move.line_ids.filtered(
                    lambda l: l.account_id == account
                )

                move_effect = sum(
                    line.debit - line.credit
                    for line in lines
                )

                future_balance = current_balance + move_effect

                if future_balance < 0:
                    raise UserError(_(
                        "Posting blocked!\n\n"
                        "Account '%s' would become negative.\n"
                        "Current balance: %s\n"
                        "After posting: %s"
                    ) % (
                        account.display_name,
                        current_balance,
                        future_balance,
                    ))

        return super().action_post()

    def _get_next_month_sequence(self, journal, date):
        year = date.year
        month = f"{date.month:02d}"

        prefix = f"{journal.code}/{year}/{month}/"

        moves = self.search([
            ("journal_id", "=", journal.id),
            ("name", "=like", prefix + "%"),
        ])

        highest = 0

        for move in moves:
            match = re.search(r"/(\d+)$", move.name or "")
            if match:
                number = int(match.group(1))
                highest = max(highest, number)

        next_number = highest + 1

        return f"{prefix}{next_number:04d}"

    def write(self, vals):
        old_names = {}

        if "date" in vals:
            for move in self:
                if (
                    move.state == "draft"
                    and move.move_type == "entry"
                    and move.journal_id
                ):
                    old_names[move.id] = move.name

                    new_date = fields.Date.to_date(vals["date"])
                    new_name = move._get_next_month_sequence(
                        move.journal_id,
                        new_date,
                    )

                    if new_name != move.name:
                        vals["name"] = new_name

        res = super().write(vals)

        for move in self:
            old_name = old_names.get(move.id)

            if old_name and old_name != move.name:
                self.env["bus.bus"]._sendone(
                    self.env.user.partner_id,
                    "simple_notification",
                    {
                        "title": "Journal Entry Number Updated",
                        "message": (
                            f"The journal entry sequence has changed "
                            f"from {old_name} to {move.name}"
                        ),
                        "type": "warning",
                        "sticky": False,
                    },
                )

        return res


    def _compute_return_picking_ids(self):
        for move in self:
            pickings = move.invoice_line_ids.mapped(
                'sale_line_ids.order_id.picking_ids'
            )

            # only returns
            return_pickings = pickings.filtered(lambda p: p.return_id)

            move.return_picking_ids = return_pickings
            move.return_picking_count = len(return_pickings)


    def action_view_returns(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Return Pickings',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.return_picking_ids.ids)],
        }


    def action_confirm_and_return(self):
        for move in self:

            if move.move_type != 'out_refund':
                raise UserError("This action only works for Credit Notes")

            # Get Sale Orders
            sale_orders = move.invoice_line_ids.mapped('sale_line_ids.order_id')
            if not sale_orders:
                raise UserError("No Sale Order found")

            # Get delivered pickings
            pickings = sale_orders.mapped('picking_ids').filtered(
                lambda p: p.state == 'done' and p.picking_type_id.code == 'outgoing'
            )

            if not pickings:
                raise UserError("No Delivered Picking found")

            picking = pickings[0]

            # Create return wizard
            return_wizard = self.env['stock.return.picking'].with_context(
                active_id=picking.id,
                active_model='stock.picking'
            ).create({})

            # Map quantities from credit note lines
            for return_line in return_wizard.product_return_moves:
                invoice_lines = move.invoice_line_ids.filtered(
                    lambda l: l.product_id == return_line.product_id
                )

                if invoice_lines:
                    qty = sum(invoice_lines.mapped('quantity'))
                    return_line.quantity = qty

            # Create return picking
            new_picking = return_wizard._create_return()

            if isinstance(new_picking, int):
                new_picking = self.env['stock.picking'].browse(new_picking)

            # Validate return picking
            new_picking.action_confirm()
            new_picking.action_assign()

            # Set done quantities correctly
            for move_line in new_picking.move_line_ids:
                move_line.quantity = move_line.move_id.product_uom_qty

            new_picking.button_validate()

            # Post credit note
            move.action_post()

        return True

    show_confirm_return_button = fields.Boolean(
        compute="_compute_show_confirm_return_button"
    )

    def _compute_show_confirm_return_button(self):
        enabled = self.env["ir.config_parameter"].sudo().get_param(
            "dekad_account_enhancement.enable_credit_note_return",
            default="False",
        ) == "True"

        for move in self:
            move.show_confirm_return_button = enabled


    def _get_sequence_format_param(self, previous):
        format_string, format_values = super()._get_sequence_format_param(previous)

        move_date = self.date or fields.Date.context_today(self)

        format_values["year"] = move_date.year
        format_values["year_length"] = 4
        format_values["month"] = move_date.month

        date_format = self.journal_id.sequence_date_format or "none"

        if date_format == "none":
            format_string = "{prefix1}{seq:0{seq_length}d}"

        elif date_format == "year":
            format_string = (
                "{prefix1}{year:0{year_length}d}/{seq:0{seq_length}d}"
            )

        elif date_format == "year_month":
            format_string = (
                "{prefix1}{year:0{year_length}d}/{month:02d}/{seq:0{seq_length}d}"
            )

        return format_string, format_values

    def _sequence_matches_date(self):
        date_format = self.journal_id.sequence_date_format or "none"

        if date_format == "none":
            return True

        return super()._sequence_matches_date()

    def _must_check_constrains_date_sequence(self):
        date_format = self.journal_id.sequence_date_format or "none"

        if date_format == "none":
            return False

        return super()._must_check_constrains_date_sequence()