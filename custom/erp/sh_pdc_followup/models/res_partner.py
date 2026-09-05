from odoo import api, fields, models, _
from odoo.tools.misc import format_date
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    pdc_followup_next_action_date = fields.Date(
        string='PDC Next Reminder',
        copy=False,
        company_dependent=True,
        help="The date before which no PDC follow-up action should be taken.",
    )

    pdc_followup_status = fields.Selection(
        [
            ('in_need_of_action', 'In need of action'),
            ('with_overdue_invoices', 'With overdue cheques'),
            ('no_action_needed', 'No action needed'),
        ],
        compute='_compute_pdc_followup_status',
        string='PDC Follow-up Status',
        search='_search_pdc_status',
        groups='account.group_account_readonly,account.group_account_invoice',
    )
    pdc_followup_line_id = fields.Many2one(
        comodel_name='pdc.followup.line',
        string='PDC Follow-up Level',
        compute='_compute_pdc_followup_status',
        inverse='_set_followup_line_on_pdc_cheques',
        search='_search_pdc_followup_line',
        groups='account.group_account_readonly,account.group_account_invoice',
    )
    pdc_followup_reminder_type = fields.Selection(
        [('automatic', 'Automatic'), ('manual', 'Manual')],
        string='PDC Reminders',
        default='automatic',
    )
    pdc_followup_responsible_id = fields.Many2one(
        comodel_name='res.users',
        string='PDC Responsible',
        copy=False,
        company_dependent=True,
        groups='account.group_account_readonly,account.group_account_invoice',
    )
    pdc_total_due = fields.Monetary(
        compute='_compute_pdc_followup_status',
        groups='account.group_account_readonly,account.group_account_invoice',
    )
    pdc_total_overdue = fields.Monetary(
        compute='_compute_pdc_followup_status',
        groups='account.group_account_readonly,account.group_account_invoice',
    )

    # Mirrors unreconciled_aml_ids: readonly=False allows manual include/exclude
    pdc_cheque_ids = fields.One2many(
        'pdc.wizard', compute='_compute_pdc_cheque_ids', readonly=False,
        string='PDC Cheques',
    )

    @api.depends('pdc_followup_next_action_date')
    @api.depends_context('company', 'allowed_company_ids')
    def _compute_pdc_cheque_ids(self):
        for partner in self:
            partner.pdc_cheque_ids = self.env['pdc.wizard'].search([
                ('partner_id', '=', partner._origin.id),
                ('payment_type', '=', 'receive_money'),
                ('state', 'in', ('registered', 'deposited')),
            ])

    @api.depends('pdc_cheque_ids', 'pdc_cheque_ids.pdc_followup_line_id',
                 'pdc_cheque_ids.due_date', 'pdc_cheque_ids.payment_amount',
                 'pdc_followup_next_action_date')
    @api.depends_context('company', 'allowed_company_ids')
    def _compute_pdc_followup_status(self):
        all_data = self._query_pdc_followup_data()
        for partner in self:
            partner_data = all_data.get(partner._origin.id, {
                'pdc_followup_status': 'no_action_needed',
                'pdc_followup_line_id': False,
            })
            partner.pdc_followup_status = partner_data['pdc_followup_status']
            partner.pdc_followup_line_id = partner_data['pdc_followup_line_id']
            partner.pdc_total_due = partner_data.get('pdc_total_due', 0.0)
            partner.pdc_total_overdue = partner_data.get('pdc_total_overdue', 0.0)

    def _query_pdc_followup_data(self, all_partners=False):
        """
        Mirrors account_followup._query_followup_data exactly.

        Key logic (same as account_followup SQL):
        - Each cheque has a stored pdc_followup_line_id (set by inverse when user manually changes level,
          or set by _update_pdc_next_followup_action_date after sending reminders).
        - The NEXT followup line after the stored one is what determines the partner level
          (i.e. the level the cheque is heading towards).
        - This means: if a cheque has stored level '8 days' and the next level is '15 days',
          the partner shows '15 days' — exactly mirroring account_followup SQL logic.
        - When user manually sets partner to '15 days', inverse stores '8 days' on cheques,
          so recompute gives back '15 days'. The level sticks.
        """
        from collections import defaultdict
        today = fields.Date.context_today(self)

        domain = [
            ('payment_type', '=', 'receive_money'),
            ('state', 'in', ('registered', 'deposited')),
        ]
        if not all_partners and self.ids:
            domain.append(('partner_id', 'in', self.ids))

        cheques = self.env['pdc.wizard'].search(domain)

        if not cheques:
            if not all_partners and self.ids:
                return {pid: {'pdc_followup_status': 'no_action_needed', 'pdc_followup_line_id': False, 'pdc_total_due': 0.0, 'pdc_total_overdue': 0.0} for pid in self.ids}
            return {}

        # Load all followup lines for this company ordered by delay asc
        all_lines = self.env['pdc.followup.line'].search(
            [('company_id', '=', self.env.company.id)], order='delay asc'
        )
        # Build next-line map: {line_id -> next_line} and {None -> first_line}
        next_line_map = {}
        prev = None
        for line in all_lines:
            next_line_map[prev] = line
            prev = line.id
        # Last line maps to itself
        if prev:
            next_line_map[prev] = all_lines[-1]

        first_line_delay = all_lines[0].delay if all_lines else 0

        # Group cheques by partner
        cheques_by_partner = defaultdict(list)
        for c in cheques:
            cheques_by_partner[c.partner_id.id].append(c)

        result = {}
        partner_ids = list(cheques_by_partner.keys()) if all_partners else (self.ids or list(cheques_by_partner.keys()))

        for partner_id in partner_ids:
            pdc_list = cheques_by_partner.get(partner_id, [])
            if not pdc_list:
                result[partner_id] = {'pdc_followup_status': 'no_action_needed', 'pdc_followup_line_id': False, 'pdc_total_due': 0.0, 'pdc_total_overdue': 0.0}
                continue

            total_due = sum(c.payment_amount for c in pdc_list)
            total_overdue = sum(c.payment_amount for c in pdc_list if c.due_date and c.due_date < today)

            # followup_delay = MAX(COALESCE(next_ful.delay, ful.delay))
            # i.e. for each cheque, take stored line's NEXT line delay (or stored line delay if no next)
            # then take the MAX across all cheques for this partner
            max_followup_delay = first_line_delay - 1  # min sentinel
            has_overdue = False
            in_need_of_action_exists = False

            for c in pdc_list:
                if c.due_date and c.due_date < today:
                    has_overdue = True

                stored_line = c.pdc_followup_line_id
                stored_line_id = stored_line.id if stored_line else None
                next_line = next_line_map.get(stored_line_id)

                if next_line:
                    cheque_delay = next_line.delay
                else:
                    cheque_delay = stored_line.delay if stored_line else (first_line_delay - 1)

                max_followup_delay = max(max_followup_delay, cheque_delay)

                # in_need_of_action: cheque is overdue relative to its stored followup line
                stored_delay = stored_line.delay if stored_line else first_line_delay

                if c.due_date:
                    trigger_date = c.due_date + timedelta(days=stored_delay)

                    if today >= trigger_date:
                        in_need_of_action_exists = True

            # Find the followup line matching max_followup_delay
            followup_line = all_lines.filtered(lambda l: l.delay == max_followup_delay)
            followup_line = followup_line[0] if followup_line else self.env['pdc.followup.line']

            if not followup_line:
                result[partner_id] = {
                    'pdc_followup_status': 'with_overdue_invoices' if has_overdue else 'no_action_needed',
                    'pdc_followup_line_id': False,
                    'pdc_total_due': total_due,
                    'pdc_total_overdue': total_overdue,
                }
                continue

            # Determine status: mirrors account_followup CASE WHEN logic
            partner = self.env['res.partner'].browse(partner_id)
            next_action = partner.pdc_followup_next_action_date
            if in_need_of_action_exists and (not next_action or next_action <= today):
                status = 'in_need_of_action'
            elif has_overdue:
                status = 'with_overdue_invoices'
            else:
                status = 'no_action_needed'

            result[partner_id] = {
                'pdc_followup_status': status,
                'pdc_followup_line_id': followup_line.id,
                'pdc_total_due': total_due,
                'pdc_total_overdue': total_overdue,
            }

        if not all_partners:
            for pid in (self.ids or []):
                if pid not in result:
                    result[pid] = {'pdc_followup_status': 'no_action_needed', 'pdc_followup_line_id': False, 'pdc_total_due': 0.0, 'pdc_total_overdue': 0.0}
        return result



    def _search_pdc_status(self, operator, value):
        if isinstance(value, str):
            value = [value]
        if operator not in ('in', '=') or not value:
            return []
        all_partners = self.search([])
        matching = [p.id for p in all_partners if p.pdc_followup_status in value]
        return [('id', 'in', matching)]

    def _search_pdc_followup_line(self, operator, value):
        if isinstance(value, str):
            domain = [('name', operator, value)]
        else:
            domain = [('id', operator, value)]
        line_ids = set(self.env['pdc.followup.line'].search(domain).ids)
        all_partners = self.search([])
        matching = [p.id for p in all_partners if p.pdc_followup_line_id.id in line_ids]
        return [('id', 'in', matching)]


    def _set_followup_line_on_pdc_cheques(self):
        """Inverse of pdc_followup_line_id.
        When the user manually sets the follow-up level on the partner,
        set the PREVIOUS level on all underlying pdc.wizard cheques
        (to indicate they have been processed up to that level).
        """
        for partner in self:
            current_followup_line = partner.pdc_followup_line_id
            previous_followup_line = self.env['pdc.followup.line'].search([
                ('delay', '<', current_followup_line.delay),
                ('company_id', '=', self.env.company.id),
            ], order='delay desc', limit=1)
            for cheque in partner.pdc_cheque_ids:
                cheque.pdc_followup_line_id = previous_followup_line

    @api.model
    def _get_first_pdc_followup_level(self):
        return self.env['pdc.followup.line'].search(
            [('company_id', '=', self.env.company.id)], order='delay asc', limit=1
        )

    def _get_pdc_followup_responsible(self):
        self.ensure_one()
        level = self.pdc_followup_line_id
        responsible_type = level.activity_default_responsible_type if level else 'followup'
        if responsible_type == 'account_manager' and self.user_id:
            return self.user_id
        if responsible_type == 'salesperson' and self.user_id:
            return self.user_id
        if self.pdc_followup_responsible_id:
            return self.pdc_followup_responsible_id
        if self.user_id:
            return self.user_id
        return self.env.user

    def _update_pdc_next_followup_action_date(self, followup_line):
        """
        After sending a reminder at followup_line level, store that level on all
        eligible cheques so the compute knows the partner has reached this level.
        """
        self.ensure_one()
        if followup_line:
            next_date = followup_line._get_next_date()
            self.pdc_followup_next_action_date = datetime.strftime(next_date, DEFAULT_SERVER_DATE_FORMAT)
            msg = _('PDC Next Reminder Date set to %s',
                    format_date(self.env, self.pdc_followup_next_action_date))
            self.message_post(body=msg)

        today = fields.Date.context_today(self)
        #  set followup_line_id on each cheque whose due date has passed this level
        previous_levels = self.env['pdc.followup.line'].search([
            ('delay', '<=', followup_line.delay if followup_line else 0),
            ('company_id', '=', self.env.company.id),
        ])
        for cheque in self.pdc_cheque_ids.filtered('due_date'):
            eligible_levels = previous_levels.filtered(
                lambda level: (today - cheque.due_date).days >= level.delay
            )
            if eligible_levels:
                cheque.pdc_followup_line_id = max(eligible_levels, key=lambda l: l.delay)

    def send_pdc_followup_email(self, options):
        """Mirrors send_followup_email."""
        for record in self:
            options['partner_id'] = record.id
            self.env['pdc.followup.report']._send_email(options)

    def send_pdc_followup_sms(self, options):
        """Mirrors send_followup_sms."""
        for partner in self:
            options['partner_id'] = partner.id
            self.env['pdc.followup.report']._send_sms(options)

    def get_pdc_followup_html(self, options=None):
        if options is None:
            options = {}
        options.update({
            'partner_id': self.id,
            'followup_line': self.pdc_followup_line_id,
        })
        return self.env['pdc.followup.report'].with_context(
            print_mode=True, lang=self.lang or self.env.user.lang
        ).get_followup_report_html(options)

    def _send_pdc_followup(self, options):

        self.ensure_one()
        followup_line = options.get('followup_line')
        if options.get('email', followup_line.send_email if followup_line else False):
            self.send_pdc_followup_email(options)
        if options.get('sms', followup_line.send_sms if followup_line else False):
            self.send_pdc_followup_sms(options)

    def _execute_pdc_followup_partner(self, options=None):
        self.ensure_one()
        if options is None:
            options = {}
        if options.get('manual_followup', self.pdc_followup_status == 'in_need_of_action'):
            followup_line = self.pdc_followup_line_id or self._get_first_pdc_followup_level()
            if not followup_line:
                return False

            if followup_line.create_activity:
                self.activity_schedule(
                    activity_type_id=followup_line.activity_type_id.id if followup_line.activity_type_id
                    else self._default_activity_type().id,
                    note=followup_line.activity_note,
                    summary=followup_line.activity_summary,
                    user_id=self._get_pdc_followup_responsible().id,
                )

            self._update_pdc_next_followup_action_date(followup_line)

            if not options.get('join_invoices', followup_line.join_invoices):
                options['attachment_ids'] = []

            self._send_pdc_followup(options={'followup_line': followup_line, **options})
            return True
        return False

    def execute_pdc_followup(self, options):
        self.ensure_one()
        to_print = self._execute_pdc_followup_partner(options=options)
        if options.get('print') and to_print:
            return self.env['pdc.followup.report']._print_followup_letter(self, options)

    def _has_missing_pdc_followup_info(self):
        self.ensure_one()
        if self.pdc_followup_line_id.send_email and not self.email:
            return True
        if self.pdc_followup_line_id.send_sms and not (self.mobile or self.phone):
            return True
        return False

    def _create_pdc_followup_missing_information_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Missing information"),
            'view_mode': 'form',
            'res_model': 'pdc.followup.missing.information.wizard',
            'target': 'new',
            'context': {'default_partner_ids': self.ids},
        }

    def action_manually_process_pdc_automatic_followups(self):
        partners_with_missing_info = self.env['res.partner']
        for partner in self:
            if partner.pdc_followup_status != 'in_need_of_action':
                continue
            if partner._has_missing_pdc_followup_info():
                partners_with_missing_info |= partner
                continue
            partner._execute_pdc_followup_partner()
        if partners_with_missing_info:
            return partners_with_missing_info._create_pdc_followup_missing_information_wizard()

    def _cron_execute_pdc_followup_company(self):
        _logger.info("=== PDC Follow-up Cron Started ===")

        followup_data = self._query_pdc_followup_data(all_partners=True)

        in_need_of_action = self.env['res.partner'].browse([
            pid for pid, d in followup_data.items()
            if d['pdc_followup_status'] == 'in_need_of_action'
        ])

        _logger.info("Partners needing action: %s", in_need_of_action.mapped('name'))

        in_need_of_action_auto = in_need_of_action.filtered(
            lambda p: p.pdc_followup_line_id.auto_execute
                      and p.pdc_followup_reminder_type == 'automatic'
        )

        _logger.info("Partners to process automatically: %s", in_need_of_action_auto.mapped('name'))

        for partner in in_need_of_action_auto:
            _logger.info(
                "Processing %s | Level=%s | Email=%s",
                partner.name,
                partner.pdc_followup_line_id.name if partner.pdc_followup_line_id else "None",
                partner.email,
            )
            try:
                partner._execute_pdc_followup_partner()
            except UserError as e:
                _logger.exception("Error processing %s", partner.name)


    def _cron_execute_pdc_followup(self):
        for company in self.env['res.company'].search([]):
            self.with_context(allowed_company_ids=company.ids)._cron_execute_pdc_followup_company()

    def action_open_overdue_pdc_cheques(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Overdue PDC Cheques'),
            'res_model': 'pdc.wizard',
            'domain': [
                ('partner_id', '=', self.id),
                ('payment_type', '=', 'receive_money'),
                ('state', 'in', ('registered', 'deposited')),
            ],
            'view_mode': 'list,form',
        }

    pdc_followup_feature_enabled = fields.Boolean(
        compute="_compute_pdc_feature"
    )

    def _compute_pdc_feature(self):
        enabled = self.env["ir.config_parameter"].sudo().get_param(
            "sh_pdc_followup.enable_pdc_followup", False
        )
        for rec in self:
            rec.pdc_followup_feature_enabled = bool(enabled)