# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import models, fields, _
from odoo.tools.sql import SQL

try:
    from odoo.addons.account_reports.models.account_report import CURRENCIES_USING_LAKH
except ImportError:
    CURRENCIES_USING_LAKH = []

# Sentinel key for AML lines that have no analytic account (NULL bucket).
_NO_ANALYTIC_KEY = '__no_analytic__'


class AccountReport(models.Model):
    _inherit = 'account.report'

    filter_secondary_currency = fields.Boolean(
        string='Secondary Currency',
        default=False,
    )

    filter_hide_initial_balance = fields.Boolean(
        string='Hide Initial Balance',
        default=False,
    )

    def _init_options_account_ids(self, options, previous_options):
        """Keep account_ids filter selection when switching dates/reports."""
        options['account_ids'] = (previous_options or {}).get('account_ids', [])

    def _get_options_domain(self, options, date_scope):
        domain = super()._get_options_domain(options, date_scope)
        if options.get('account_ids'):
            domain.append(('account_id', 'in', options['account_ids']))
        return domain

    def _init_options_hide_initial_balance(self, options, previous_options):
        """
        Add hide_initial_balance option to reports with filter_hide_initial_balance
        enabled (General Ledger only, via data/account_report_data.xml).
        Auto-discovered by _get_options_initializers_in_sequence (prefix convention).
        """
        if not self.filter_hide_initial_balance:
            return
        options['hide_initial_balance'] = (previous_options or {}).get('hide_initial_balance', False)

    filter_hide_zero_balance = fields.Boolean(
        string='Hide Zero Balance',
        default=False,
    )

    # =========================================================================
    # OPTIONS: Hide Zero Balance Filter
    # =========================================================================

    def _init_options_hide_zero_balance(self, options, previous_options):
        """
        Add hide_zero_balance option to reports with filter_hide_zero_balance enabled.

        For Trial Balance: syncs with hide_0_lines so setLineVisibility() fires
        client-side to hide zero-balance accounts.

        For Partner Ledger: hide_zero_balance is injected via
        PartnerLedgerCustomHandlerHideZero._custom_options_initializer instead,
        because Partner Ledger uses its own options initializer chain.

        Auto-discovered by _get_options_initializers_in_sequence (prefix convention).
        Runs at sequence 220 (after secondary currency at 210).
        """
        if not self.filter_hide_zero_balance:
            return

        prev = (previous_options or {}).get('hide_zero_balance', False)
        options['hide_zero_balance'] = prev

    def _get_options_initializers_forced_sequence_map(self):
        res = super()._get_options_initializers_forced_sequence_map()
        res[self._init_options_hide_zero_balance] = 220
        return res

    # =========================================================================
    # OPTIONS: Secondary Currency Filter
    # =========================================================================

    def _init_options_secondary_currency(self, options, previous_options):
        """
        Add secondary currency single-select filter to all accounting reports.
        Loads all active currencies except the company's own currency.
        Auto-discovered by _get_options_initializers_in_sequence (prefix convention).
        Runs at sequence 210 (after rounding_unit at 200).

        Stores a fallback_rate in options for AML rows that have no historical
        rate in res_currency_rate (e.g. old data with no rate entries).
        """
        if not self.filter_secondary_currency:
            return

        company_currency = self.env.company.currency_id

        available_currencies = self.env['res.currency'].search([
            ('active', '=', True),
            ('id', '!=', company_currency.id),
        ])

        if not available_currencies:
            return

        prev_id = (previous_options or {}).get('secondary_currency_id', False)
        if prev_id and prev_id not in available_currencies.ids:
            prev_id = False

        options['secondary_currencies'] = [
            {
                'id': c.id,
                'name': c.name,
                'symbol': c.symbol,
                'selected': (c.id == prev_id),
            }
            for c in available_currencies
        ]
        options['secondary_currency_id'] = prev_id

        # Fallback rate: used when no historical rate exists for a given AML date.
        # Computed once here via _get_conversion_rate (today's rate).
        if prev_id:
            sec_currency = self.env['res.currency'].browse(prev_id)
            options['secondary_currency_rate'] = company_currency._get_conversion_rate(
                company_currency, sec_currency,
                self.env.company, fields.Date.today(),
            )
        else:
            options['secondary_currency_rate'] = False

    def _get_options_initializers_forced_sequence_map(self):
        """Run secondary currency init AFTER rounding_unit (200) so we can patch its names."""
        res = super()._get_options_initializers_forced_sequence_map()
        res[self._init_options_secondary_currency] = 210
        return res

    # =========================================================================
    # ROUNDING UNIT: patch labels when secondary currency is active
    # =========================================================================

    def _init_options_rounding_unit(self, options, previous_options):
        """
        Call super() first to get standard company-currency unit names,
        then replace with secondary currency labels if one is selected.
        e.g. AED / kAED / MAED  →  SYP / kSYP / MSYP
        """
        super()._init_options_rounding_unit(options, previous_options)

        prev_currency_id = (previous_options or {}).get('secondary_currency_id', False)
        if not prev_currency_id:
            return

        currency = self.env['res.currency'].browse(prev_currency_id)
        if not currency.exists() or not currency.active:
            return

        symbol = currency.symbol
        name = currency.name

        rounding_unit_names = [
            ('decimals',  (f'.{symbol}', '')),
            ('units',     (f'{symbol}',  '')),
            ('thousands', (f'K{symbol}', _('Amounts in Thousands'))),
            ('millions',  (f'M{symbol}', _('Amounts in Millions'))),
        ]
        if name in CURRENCIES_USING_LAKH:
            rounding_unit_names.insert(3, ('lakhs', (f'L{symbol}', _('Amounts in Lakhs'))))

        options['rounding_unit_names'] = dict(rounding_unit_names)

    # =========================================================================
    # CURRENCY SYMBOL: patch report header + column formatting
    # =========================================================================

    def _generate_common_warnings(self, options, warnings):
        """
        Override to add a warning when the fallback rate (today's rate) is being
        used because no historical rate exists for some AML dates.
        """
        super()._generate_common_warnings(options, warnings)

        sec_id = options.get('secondary_currency_id')
        if not sec_id:
            return

        date_from = options.get('date', {}).get('date_from')
        if not date_from:
            return

        # Get all companies in this report (multi-company support)
        report_company_ids = self.get_report_company_ids(options)

        earliest_rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', sec_id),
            ('company_id', 'in', [False] + list(report_company_ids)),
        ], order='name asc', limit=1)

        if not earliest_rate:
            warnings['dekad_accounting_reports_enhanced.warning_no_rate'] = {
                'alert_type': 'warning',
            }
            return

        date_from_obj = fields.Date.from_string(date_from)
        if date_from_obj < earliest_rate.name:
            warnings['dekad_accounting_reports_enhanced.warning_fallback_rate'] = {
                'alert_type': 'warning',
                'earliest_rate_date': str(earliest_rate.name),
            }

    def get_report_information(self, options):
        """
        Override to:
        1. Replace company_currency_symbol with secondary currency symbol
           when a secondary currency is selected.
        2. Add selected analytic accounts / active custom filters info
           to options so the PDF filter header can display them.
        """
        result = super().get_report_information(options)

        # ── Secondary currency symbol ─────────────────────────────────────────
        sec_id = options.get('secondary_currency_id')
        if sec_id:
            currency = self.env['res.currency'].browse(sec_id)
            if currency.exists() and currency.active:
                result['report']['company_currency_symbol'] = currency.symbol

        # ── Custom filter labels for PDF header ───────────────────────────────
        custom_filter_labels = []

        # Analytic accounts filter (native Odoo analytic filter)
        # options['analytic_accounts'] can be a list of ints (ids) or dicts
        raw_analytic = options.get('analytic_accounts', [])
        if raw_analytic and isinstance(raw_analytic[0], dict):
            analytic_ids = [aa['id'] for aa in raw_analytic if aa.get('selected')]
        else:
            analytic_ids = [aa for aa in raw_analytic if isinstance(aa, int)]
        if analytic_ids:
            accounts = self.env['account.analytic.account'].browse(analytic_ids)
            custom_filter_labels.append(
                'Analytic Account: ' + ', '.join(accounts.mapped('name'))
            )

        # Group by Analytic
        if options.get('group_by_analytic'):
            custom_filter_labels.append('Grouped by: Analytic Account')

        # Group by Company
        if options.get('group_by_company'):
            custom_filter_labels.append('Grouped by: Company')

        # Hide Initial Balance
        if options.get('hide_initial_balance'):
            custom_filter_labels.append('Hide Initial Balance')

        # Secondary currency label
        if sec_id:
            currency = self.env['res.currency'].browse(sec_id)
            if currency.exists():
                custom_filter_labels.append('Currency: ' + currency.name)

        # Account filter
        account_ids = options.get('account_ids', [])
        if account_ids:
            accounts = self.env['account.account'].browse(account_ids)
            custom_filter_labels.append(
                'Accounts: ' + ', '.join(accounts.mapped('code'))
            )

        if custom_filter_labels:
            # Add to options so the PDF template can access them via 'options'
            # (render_values passes options directly to the QWeb template,
            # but result keys other than known ones are not forwarded)
            options['custom_filter_labels'] = custom_filter_labels

        return result

    def _build_column_dict(
            self, col_value, col_data,
            options=None, currency=False, digits=1,
            column_expression=None, has_sublines=False,
            report_line_id=None,
    ):
        """
        Override to inject secondary currency into monetary column format_params.
        This makes formatLang use the secondary currency symbol and decimal places.
        """
        result = super()._build_column_dict(
            col_value, col_data,
            options=options, currency=currency, digits=digits,
            column_expression=column_expression, has_sublines=has_sublines,
            report_line_id=report_line_id,
        )

        options = options or {}
        sec_id = options.get('secondary_currency_id')
        if not sec_id:
            return result

        # Only patch monetary columns
        if result.get('figure_type', 'string') != 'monetary':
            return result

        # Don't override if column already has an explicit foreign currency
        # (e.g. the amount_currency column in General Ledger)
        company_currency_id = self.env.company.currency_id.id
        if result.get('format_params', {}).get('currency_id', company_currency_id) != company_currency_id:
            return result

        result.setdefault('format_params', {})
        result['format_params']['currency_id'] = sec_id

        return result

    # =========================================================================
    # SQL HELPERS
    #
    # Per-line conversion using LATERAL JOIN on res_currency_rate:
    #   Each AML row is converted at the rate that was active on its own date.
    #   This means SUM() naturally accumulates historically-correct values.
    #
    # Logic per AML row:
    #   currency_id == secondary  →  amount_currency  (already in target currency)
    #   otherwise                 →  balance * rate_on_aml_date
    #
    # rate stored in res_currency_rate = secondary_units per 1 company_unit
    # e.g. company=USD, secondary=SYP: rate = 10 means 1 USD = 10 SYP
    # So: balance_usd * 10 = balance_syp  ✓
    #
    # The LATERAL subquery fetches the closest rate <= aml.date, preferring
    # company-specific rates over global (company_id IS NULL) ones.
    # Falls back to options['secondary_currency_rate'] (today's rate) when
    # no historical entry exists at all.
    #
    # aml_alias parameter lets helpers work on both 'account_move_line' (direct
    # table queries) and 'base' (super() subquery alias in _get_query_amls).
    # =========================================================================

    def _get_lateral_rate_sql(self, options, aml_alias: str = 'account_move_line') -> SQL:
        """
        Returns a LATERAL subquery SQL fragment that resolves the historical
        conversion rate for each AML row.

        Result column name: sec_rate_value
        Usage: LEFT JOIN LATERAL (...) _sec_rate ON true

        Rate direction: res_currency_rate.rate = secondary_units per 1 company_unit
        e.g. company=USD, secondary=SYP: rate=10 → balance_usd * 10 = balance_syp
        Falls back to options['secondary_currency_rate'] when no historical row exists.

        Date ambiguity note: when aml_alias='base' (wrapping super()._get_query_amls),
        the inner SELECT contains two columns named 'date':
          - account_move_line.date       (no alias, col #3)
          - account_move_line.date AS date  (col #13)
        PostgreSQL raises AmbiguousColumn on base.date.
        Fix: fetch date from account_move_line directly via base.id — unambiguous
        and always correct since base.id is the AML primary key.
        """
        sec_id = options.get('secondary_currency_id')
        fallback = options.get('secondary_currency_rate', 1.0)

        if aml_alias == 'account_move_line':
            # Direct table — no ambiguity
            aml_date = SQL("account_move_line.date")
            aml_company = SQL("account_move_line.company_id")
        else:
            # Subquery alias 'base' has two columns named 'date' (ambiguous).
            # Fix: fetch date directly from account_move_line via base.id.
            # base.id is unambiguous and is the AML primary key.
            aml_date = SQL(
                "(SELECT aml_d.date FROM account_move_line aml_d WHERE aml_d.id = %s.id)",
                SQL(aml_alias),
            )
            aml_company = SQL(f"{aml_alias}.company_id")

        return SQL(
            """LEFT JOIN LATERAL (
                SELECT COALESCE(
                    (
                        SELECT rcr.rate
                        FROM res_currency_rate rcr
                        WHERE rcr.currency_id = %(sec_id)s
                          AND rcr.name <= %(aml_date)s
                          AND (rcr.company_id = %(aml_company)s
                               OR rcr.company_id IS NULL)
                        ORDER BY
                            CASE WHEN rcr.company_id = %(aml_company)s
                                 THEN 0 ELSE 1 END,
                            rcr.name DESC
                        LIMIT 1
                    ),
                    %(fallback)s
                ) AS sec_rate_value
            ) _sec_rate ON true""",
            sec_id=sec_id,
            aml_date=aml_date,
            aml_company=aml_company,
            fallback=fallback,
        )

    def _get_secondary_currency_balance(self, options, aml_alias: str = 'account_move_line') -> SQL:
        """
        Returns a SQL expression for effective balance in secondary currency.

        Expects _sec_rate lateral join to be present in the FROM clause.
        When called from _get_query_amls / _get_query_sums / _get_initial_balance_values,
        the lateral join is added automatically.
        """
        sec_id = options.get('secondary_currency_id')
        if not sec_id:
            return self._currency_table_apply_rate(SQL(f"{aml_alias}.balance"))

        aml = SQL(aml_alias)

        return SQL(
            """CASE
                WHEN %(aml)s.currency_id = %(sec_id)s
                    THEN %(aml)s.amount_currency
                    -- AML is already in secondary currency → use amount_currency directly

                ELSE %(aml)s.balance * _sec_rate.sec_rate_value
                    -- balance is ALWAYS stored in company currency (guaranteed by Odoo).
                    -- rate = secondary_units per 1 company_unit (e.g. 10 SYP per USD)
                    -- This handles two cases correctly:
                    --   a) AML in company currency → balance * rate = secondary value
                    --   b) AML in a third currency (e.g. EUR when company=USD, secondary=SYP)
                    --      Odoo already converted EUR→USD at post time, balance is in USD
                    --      balance * rate gives correct SYP value
            END""",
            aml=aml,
            sec_id=sec_id,
        )

    def _get_secondary_currency_debit(self, options, aml_alias: str = 'account_move_line') -> SQL:
        """Effective debit = GREATEST(balance_in_secondary, 0)"""
        if not options.get('secondary_currency_id'):
            return self._currency_table_apply_rate(SQL(f"{aml_alias}.debit"))

        return SQL(
            "GREATEST(%(balance)s, 0)",
            balance=self._get_secondary_currency_balance(options, aml_alias),
        )

    def _get_secondary_currency_credit(self, options, aml_alias: str = 'account_move_line') -> SQL:
        """Effective credit = GREATEST(-balance_in_secondary, 0)"""
        if not options.get('secondary_currency_id'):
            return self._currency_table_apply_rate(SQL(f"{aml_alias}.credit"))

        return SQL(
            "GREATEST(-1 * (%(balance)s), 0)",
            balance=self._get_secondary_currency_balance(options, aml_alias),
        )


class AccountGeneralLedgerReportHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    # =========================================================================
    # ANALYTIC ACCOUNT — two independent features:
    #
    # 1. SHOW ANALYTIC ACCOUNT (column)
    #    Adds an optional "Analytic Account" column toggled via Options dropdown.
    #    Uses account_move_line.analytic_account_id (stored field, this module).
    #    Works at AML level — only meaningful on General Ledger.
    #
    # 2. GROUP BY ANALYTIC ACCOUNT (layout restructure)
    #    Adds a "Group by Analytic Account" toggle via Options dropdown.
    #    Restructures the report as:
    #        Analytic Account (level 1, unfoldable)
    #          └── Account   (level 2, unfoldable)
    #                └── Initial Balance + AML lines (level 3)
    #    Lines with no analytic appear last under "∅ No Analytic Account".
    #
    # Both features are independent — can be used together or separately.
    # When group_by_analytic is on, the analytic column is redundant (every
    # section already belongs to one analytic) but still allowed if the user
    # enables both.
    #
    # Performance:
    # - Analytic totals: single SQL GROUP BY (no N+1 queries).
    # - analytic_account_id is a stored field — no runtime join.
    # - Account/AML expansion delegates to Odoo's existing handlers via
    #   forced_domain injection (load-more, initial balance, unfold-all intact).
    # =========================================================================

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        # ── Show Analytic Account column ──────────────────────────────────────
        options['show_analytic_account'] = (previous_options or {}).get('show_analytic_account', False)
        if not options['show_analytic_account']:
            options['columns'] = [
                col for col in options['columns']
                if col['expression_label'] != 'analytic_account'
            ]

        # ── Group by Analytic Account ─────────────────────────────────────────
        options['group_by_analytic'] = (previous_options or {}).get('group_by_analytic', False)

        # ── Group by Company ──────────────────────────────────────────────────
        # Mutually exclusive with group_by_analytic:
        # activating one automatically deactivates the other.
        options['group_by_company'] = (previous_options or {}).get('group_by_company', False)
        if options['group_by_company'] and options['group_by_analytic']:
            # The one that changed last wins; if both somehow arrive True at the
            # same time we favour group_by_company (it was just toggled on).
            options['group_by_analytic'] = False

        # ── Show Company column ───────────────────────────────────────────────
        options['show_company_column'] = (previous_options or {}).get('show_company_column', False)
        if not options['show_company_column']:
            options['columns'] = [
                col for col in options['columns']
                if col['expression_label'] != 'company_name'
            ]

    # =========================================================================
    # GROUP BY ANALYTIC — dynamic lines generator
    # =========================================================================

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        """
        Routing:
          group_by_company on  → Company title lines (lazy expand)
          group_by_analytic on → Analytic Account title lines (lazy expand)
          both off             → standard General Ledger via super() (zero risk)
        The two group-by modes are mutually exclusive (enforced in
        _custom_options_initializer).
        """
        if options.get('group_by_company'):
            lines = []
            totals_by_column_group = defaultdict(lambda: {'debit': 0.0, 'credit': 0.0, 'balance': 0.0})
            for company, col_group_totals in self._query_company_totals(report, options):
                for col_group_key, vals in col_group_totals.items():
                    totals_by_column_group[col_group_key]['debit']   += vals.get('debit',   0.0)
                    totals_by_column_group[col_group_key]['credit']  += vals.get('credit',  0.0)
                    totals_by_column_group[col_group_key]['balance'] += vals.get('balance', 0.0)
                lines.append(self._get_company_title_line(report, options, company, col_group_totals))
            lines.append(self._get_total_line(report, options, totals_by_column_group))
            return [(0, line) for line in lines]

        if options.get('group_by_analytic'):
            lines = []
            totals_by_column_group = defaultdict(lambda: {'debit': 0.0, 'credit': 0.0, 'balance': 0.0})
            for analytic_key, display_name, col_group_totals in self._query_analytic_totals(report, options):
                for col_group_key, vals in col_group_totals.items():
                    totals_by_column_group[col_group_key]['debit']   += vals.get('debit',   0.0)
                    totals_by_column_group[col_group_key]['credit']  += vals.get('credit',  0.0)
                    totals_by_column_group[col_group_key]['balance'] += vals.get('balance', 0.0)
                lines.append(self._get_analytic_title_line(
                    report, options, analytic_key, display_name, col_group_totals,
                ))
            lines.append(self._get_total_line(report, options, totals_by_column_group))
            return [(0, line) for line in lines]

        return super()._dynamic_lines_generator(
            report, options, all_column_groups_expression_totals, warnings=warnings,
        )

    # =========================================================================
    # GROUP BY ANALYTIC — totals query (single SQL round-trip)
    # =========================================================================

    def _query_analytic_totals(self, report, options):
        """
        Single UNION ALL query across all column groups.
        Returns [(analytic_key, display_name, {col_group_key: {debit,credit,balance}})]
        Named accounts sorted by name; NULL bucket always last.
        """
        options_by_column_group = report._split_options_per_column_group(options)
        queries = []

        for column_group_key, options_group in options_by_column_group.items():
            query = report._get_report_query(options_group, 'from_beginning')
            queries.append(SQL(
                """
                SELECT
                    account_move_line.analytic_account_id       AS analytic_id,
                    %(column_group_key)s                        AS column_group_key,
                    SUM(%(debit_select)s)                       AS debit,
                    SUM(%(credit_select)s)                      AS credit,
                    SUM(%(balance_select)s)                     AS balance
                FROM %(table_references)s
                %(currency_table_join)s
                WHERE %(search_condition)s
                GROUP BY account_move_line.analytic_account_id
                """,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                currency_table_join=report._currency_table_aml_join(options_group),
                search_condition=query.where_clause,
            ))

        if not queries:
            return []

        self._cr.execute(SQL(" UNION ALL ").join(queries))
        rows = self._cr.dictfetchall()
        if not rows:
            return []

        named_totals = {}
        null_totals  = {}
        analytic_ids = set()

        for row in rows:
            aid = row['analytic_id']
            cgk = row['column_group_key']
            vals = {
                'debit':   row['debit']   or 0.0,
                'credit':  row['credit']  or 0.0,
                'balance': row['balance'] or 0.0,
            }
            if aid is None:
                null_totals[cgk] = vals
            else:
                analytic_ids.add(aid)
                named_totals.setdefault(aid, {})[cgk] = vals

        result = []
        if analytic_ids:
            for aa in self.env['account.analytic.account'].search([('id', 'in', list(analytic_ids))]):
                result.append((aa.id, aa.display_name, named_totals[aa.id]))

        if null_totals:
            result.append((_NO_ANALYTIC_KEY, _('∅ No Analytic Account'), null_totals))

        return result

    # =========================================================================
    # GROUP BY ANALYTIC — analytic title line builder
    # =========================================================================

    def _get_analytic_title_line(self, report, options, analytic_key, display_name, col_group_totals):
        line_columns = []
        for column in options['columns']:
            col_expr = column['expression_label']
            col_val = None
            if col_expr in ('debit', 'credit', 'balance'):
                col_val = col_group_totals.get(column['column_group_key'], {}).get(col_expr)
            line_columns.append(report._build_column_dict(col_val, column, options=options))

        if analytic_key == _NO_ANALYTIC_KEY:
            line_id = report._get_generic_line_id(None, None, markup='no_analytic')
        else:
            line_id = report._get_generic_line_id('account.analytic.account', analytic_key)

        is_unfolded = (
            any('no_analytic' in lid for lid in options.get('unfolded_lines', []))
            if analytic_key == _NO_ANALYTIC_KEY
            else any(
                report._get_res_id_from_line_id(lid, 'account.analytic.account') == analytic_key
                for lid in options.get('unfolded_lines', [])
            )
        )

        return {
            'id': line_id,
            'name': display_name,
            'columns': line_columns,
            'level': 1,
            'unfoldable': True,
            'unfolded': is_unfolded or options.get('unfold_all', False),
            'expand_function': '_report_expand_unfoldable_line_analytic_gl',
        }

    # =========================================================================
    # GROUP BY ANALYTIC — expand analytic → account lines
    # =========================================================================

    def _report_expand_unfoldable_line_analytic_gl(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        report = self.env.ref('account_reports.general_ledger_report')

        markup = report._get_markup(line_dict_id)
        is_no_analytic = (markup == 'no_analytic')

        if is_no_analytic:
            analytic_domain = [('analytic_account_id', '=', False)]
        else:
            analytic_id = report._get_res_id_from_line_id(line_dict_id, 'account.analytic.account')
            if not analytic_id:
                return {'lines': [], 'offset_increment': 0, 'has_more': False}
            analytic_domain = [('analytic_account_id', '=', analytic_id)]

        scoped_options = {
            **options,
            'forced_domain': options.get('forced_domain', []) + analytic_domain,
        }

        lines = []
        date_from = options['date']['date_from']

        for account, column_group_results in self._query_values(report, scoped_options):
            eval_dict = {}
            has_lines = False

            for col_group_key, results in column_group_results.items():
                account_sum     = results.get('sum', {})
                account_un_earn = results.get('unaffected_earnings', {})

                eval_dict[col_group_key] = {
                    'amount_currency': (
                        account_sum.get('amount_currency', 0.0)
                        + account_un_earn.get('amount_currency', 0.0)
                    ),
                    'debit':   account_sum.get('debit',   0.0) + account_un_earn.get('debit',   0.0),
                    'credit':  account_sum.get('credit',  0.0) + account_un_earn.get('credit',  0.0),
                    'balance': account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0),
                }

                max_date = account_sum.get('max_date')
                has_lines = has_lines or bool(max_date and str(max_date) >= date_from)

            account_line = self._get_account_title_line(report, scoped_options, account, has_lines, eval_dict)
            account_line['parent_id'] = line_dict_id
            account_line['level'] = 2
            account_line['id'] = report._build_subline_id(line_dict_id, account_line['id'])

            if has_lines:
                account_line['expand_function'] = '_report_expand_unfoldable_line_analytic_account_gl'
                if account_line['id'] in options.get('unfolded_lines', []):
                    account_line['unfolded'] = True

            lines.append(account_line)

        return {'lines': lines, 'offset_increment': len(lines), 'has_more': False}

    # =========================================================================
    # GROUP BY ANALYTIC — expand account → AML lines (keeps analytic scope)
    # =========================================================================

    def _report_expand_unfoldable_line_analytic_account_gl(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """
        Thin wrapper: injects analytic forced_domain then delegates to Odoo's
        standard GL expand handler.

        Same batch issue as company_account_gl: our account lines under analytic
        groups are not pre-loaded in unfold_all_batch_data. We build a minimal
        batch for this single account scoped to the correct analytic domain.
        """
        report = self.env.ref('account_reports.general_ledger_report')

        markup = report._get_markup(line_dict_id)
        is_no_analytic = (markup == 'no_analytic')

        if is_no_analytic:
            analytic_domain = [('analytic_account_id', '=', False)]
        else:
            analytic_id = report._get_res_id_from_line_id(line_dict_id, 'account.analytic.account')
            analytic_domain = [('analytic_account_id', '=', analytic_id)] if analytic_id else []

        scoped_options = options
        if analytic_domain:
            scoped_options = {
                **options,
                'forced_domain': options.get('forced_domain', []) + analytic_domain,
            }

        # Strip analytic prefix so _get_model_info_from_id returns account.account
        parsed = report._parse_line_id(line_dict_id)
        actual_line_id = report._build_line_id([parsed[-1]])
        _, account_id = report._get_model_info_from_id(actual_line_id)

        # Build minimal batch for this account scoped to the analytic domain
        if unfold_all_batch_data is not None and account_id:
            limit_to_load = report.load_more_limit if report.load_more_limit and not scoped_options.get('export_mode') else None
            aml_results_all, _ = self._get_aml_values(report, scoped_options, [account_id])
            aml_results = aml_results_all.get(account_id, {})
            if limit_to_load:
                has_more = len(aml_results) > limit_to_load
                aml_results = dict(list(aml_results.items())[:limit_to_load])
            else:
                has_more = False

            unfold_all_batch_data = {
                'initial_balances': self._get_initial_balance_values(report, [account_id], scoped_options),
                'aml_results': {account_id: aml_results},
                'has_more': {account_id: has_more},
            }

        return self._report_expand_unfoldable_line_general_ledger(
            actual_line_id, groupby, scoped_options, progress, offset,
            unfold_all_batch_data=unfold_all_batch_data,
        )

    # =========================================================================
    # SHOW ANALYTIC ACCOUNT COLUMN — query override
    # =========================================================================


    # =========================================================================
    # GROUP BY COMPANY — totals query (single SQL round-trip)
    # =========================================================================

    def _query_company_totals(self, report, options):
        """
        Single UNION ALL query across all column groups.
        Returns [(res.company, {col_group_key: {debit, credit, balance}})]
        sorted by company name.
        company_id is a direct column on account_move_line — no join needed.
        """
        options_by_column_group = report._split_options_per_column_group(options)
        queries = []

        for column_group_key, options_group in options_by_column_group.items():
            query = report._get_report_query(options_group, 'from_beginning')
            queries.append(SQL(
                """
                SELECT
                    account_move_line.company_id                AS company_id,
                    %(column_group_key)s                        AS column_group_key,
                    SUM(%(debit_select)s)                       AS debit,
                    SUM(%(credit_select)s)                      AS credit,
                    SUM(%(balance_select)s)                     AS balance
                FROM %(table_references)s
                %(currency_table_join)s
                WHERE %(search_condition)s
                GROUP BY account_move_line.company_id
                """,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                currency_table_join=report._currency_table_aml_join(options_group),
                search_condition=query.where_clause,
            ))

        if not queries:
            return []

        self._cr.execute(SQL(" UNION ALL ").join(queries))
        rows = self._cr.dictfetchall()
        if not rows:
            return []

        totals_by_company = {}
        company_ids = set()
        for row in rows:
            cid = row['company_id']
            company_ids.add(cid)
            totals_by_company.setdefault(cid, {})[row['column_group_key']] = {
                'debit':   row['debit']   or 0.0,
                'credit':  row['credit']  or 0.0,
                'balance': row['balance'] or 0.0,
            }

        companies = self.env['res.company'].search([('id', 'in', list(company_ids))])
        return [(company, totals_by_company[company.id]) for company in companies]

    # =========================================================================
    # GROUP BY COMPANY — company title line builder
    # =========================================================================

    def _get_company_title_line(self, report, options, company, col_group_totals):
        """
        Builds the level-1 collapsible line for a company.
        Numeric columns (debit/credit/balance) show aggregated totals;
        string/date columns are blank — no meaning at company level.
        """
        line_columns = []
        for column in options['columns']:
            col_val = None
            if column['expression_label'] in ('debit', 'credit', 'balance'):
                col_val = col_group_totals.get(column['column_group_key'], {}).get(
                    column['expression_label']
                )
            line_columns.append(report._build_column_dict(col_val, column, options=options))

        line_id = report._get_generic_line_id('res.company', company.id)
        is_unfolded = any(
            report._get_res_id_from_line_id(lid, 'res.company') == company.id
            for lid in options.get('unfolded_lines', [])
        )

        return {
            'id': line_id,
            'name': company.display_name,
            'columns': line_columns,
            'level': 1,
            'unfoldable': True,
            'unfolded': is_unfolded or options.get('unfold_all', False),
            'expand_function': '_report_expand_unfoldable_line_company_gl',
        }

    # =========================================================================
    # GROUP BY COMPANY — expand company → account lines
    # =========================================================================

    def _report_expand_unfoldable_line_company_gl(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """
        Called when the user expands a Company title line.
        Scopes _query_values() to this company via forced_domain,
        then renders account lines at level 2.
        """
        report = self.env.ref('account_reports.general_ledger_report')
        company_id = report._get_res_id_from_line_id(line_dict_id, 'res.company')

        if not company_id:
            return {'lines': [], 'offset_increment': 0, 'has_more': False}

        scoped_options = {
            **options,
            'forced_domain': options.get('forced_domain', []) + [('company_id', '=', company_id)],
        }

        lines = []
        date_from = options['date']['date_from']

        for account, column_group_results in self._query_values(report, scoped_options):
            eval_dict = {}
            has_lines = False

            for col_group_key, results in column_group_results.items():
                account_sum     = results.get('sum', {})
                account_un_earn = results.get('unaffected_earnings', {})

                eval_dict[col_group_key] = {
                    'amount_currency': (
                        account_sum.get('amount_currency', 0.0)
                        + account_un_earn.get('amount_currency', 0.0)
                    ),
                    'debit':   account_sum.get('debit',   0.0) + account_un_earn.get('debit',   0.0),
                    'credit':  account_sum.get('credit',  0.0) + account_un_earn.get('credit',  0.0),
                    'balance': account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0),
                }

                max_date = account_sum.get('max_date')
                has_lines = has_lines or bool(max_date and str(max_date) >= date_from)

            account_line = self._get_account_title_line(report, scoped_options, account, has_lines, eval_dict)
            account_line['parent_id'] = line_dict_id
            account_line['level'] = 2
            account_line['id'] = report._build_subline_id(line_dict_id, account_line['id'])

            if has_lines:
                account_line['expand_function'] = '_report_expand_unfoldable_line_company_account_gl'
                if account_line['id'] in options.get('unfolded_lines', []):
                    account_line['unfolded'] = True

            lines.append(account_line)

        return {'lines': lines, 'offset_increment': len(lines), 'has_more': False}

    # =========================================================================
    # GROUP BY COMPANY — expand account → AML lines (keeps company scope)
    # =========================================================================

    def _report_expand_unfoldable_line_company_account_gl(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """
        Thin wrapper: injects company forced_domain then delegates to Odoo's
        standard GL expand handler.

        Our account lines are not pre-loaded in unfold_all_batch_data because
        they appear only after expanding company lines — the batch generator
        runs before any expansion and never sees them.

        When unfold_all_batch_data is present, we build a minimal batch for
        this single account on-the-fly using the same helpers Odoo uses,
        scoped to the correct company via forced_domain. This preserves the
        single-query-per-account efficiency while avoiding the KeyError.
        """
        report = self.env.ref('account_reports.general_ledger_report')
        company_id = report._get_res_id_from_line_id(line_dict_id, 'res.company')

        scoped_options = options
        if company_id:
            scoped_options = {
                **options,
                'forced_domain': options.get('forced_domain', []) + [('company_id', '=', company_id)],
            }

        # Strip company prefix so _get_model_info_from_id returns account.account
        parsed = report._parse_line_id(line_dict_id)
        actual_line_id = report._build_line_id([parsed[-1]])
        _, account_id = report._get_model_info_from_id(actual_line_id)

        # Build a minimal batch for this single account scoped to the company.
        # This gives us the same efficiency as the standard batch (one query
        # per call) while keeping the correct company scope.
        if unfold_all_batch_data is not None:
            limit_to_load = report.load_more_limit if report.load_more_limit and not scoped_options.get('export_mode') else None
            aml_results_all, _ = self._get_aml_values(report, scoped_options, [account_id])
            aml_results = aml_results_all.get(account_id, {})
            if limit_to_load:
                has_more = len(aml_results) > limit_to_load
                aml_results = dict(list(aml_results.items())[:limit_to_load])
            else:
                has_more = False

            unfold_all_batch_data = {
                'initial_balances': self._get_initial_balance_values(report, [account_id], scoped_options),
                'aml_results': {account_id: aml_results},
                'has_more': {account_id: has_more},
            }

        return self._report_expand_unfoldable_line_general_ledger(
            actual_line_id, groupby, scoped_options, progress, offset,
            unfold_all_batch_data=unfold_all_batch_data,
        )

    def _get_initial_balance_values(self, report, account_ids, options):
        """
        Full override to apply per-line historical rate conversion.

        We cannot use super() as a subquery here because _get_initial_balance_values
        executes its query internally and returns a dict, not a SQL object.
        We mirror the original structure exactly but inject the LATERAL rate join
        and per-line CASE WHEN conversion before SUM().
        """
        if not options.get('secondary_currency_id'):
            return super()._get_initial_balance_values(report, account_ids, options)

        queries = []
        for column_group_key, options_group in report._split_options_per_column_group(options).items():
            new_options = self._get_options_initial_balance(options_group)
            domain = [('account_id', 'in', account_ids)]
            if not new_options.get('general_ledger_strict_range'):
                domain += [
                    '|',
                    ('date', '>=', new_options['date']['date_from']),
                    ('account_id.include_initial_balance', '=', True),
                ]
            if new_options.get('include_current_year_in_unaff_earnings'):
                domain += [('account_id.include_initial_balance', '=', True)]

            query = report._get_report_query(new_options, 'from_beginning', domain=domain)
            queries.append(SQL(
                """
                SELECT
                    account_move_line.account_id                          AS groupby,
                    'initial_balance'                                     AS key,
                    NULL                                                  AS max_date,
                    %(column_group_key)s                                  AS column_group_key,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0) AS amount_currency,
                    COALESCE(SUM(%(debit_select)s), 0.0)                  AS debit,
                    COALESCE(SUM(%(credit_select)s), 0.0)                 AS credit,
                    COALESCE(SUM(%(balance_select)s), 0.0)                AS balance
                FROM %(table_references)s
                %(currency_table_join)s
                %(lateral_rate_join)s
                WHERE %(search_condition)s
                GROUP BY account_move_line.account_id
                """,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(options_group),
                lateral_rate_join=self._get_lateral_rate_sql(options_group),
                debit_select=self._get_secondary_currency_debit(options_group),
                credit_select=self._get_secondary_currency_credit(options_group),
                balance_select=self._get_secondary_currency_balance(options_group),
                search_condition=query.where_clause,
            ))

        self._cr.execute(SQL(" UNION ALL ").join(queries))

        init_balance_by_col_group = {
            account_id: {column_group_key: {} for column_group_key in options['column_groups']}
            for account_id in account_ids
        }
        for result in self._cr.dictfetchall():
            init_balance_by_col_group[result['groupby']][result['column_group_key']] = result

        accounts = self.env['account.account'].browse(account_ids)
        return {
            account.id: (account, init_balance_by_col_group[account.id])
            for account in accounts
        }

    def _get_query_amls(self, report, options, expanded_account_ids, offset=0, limit=None) -> SQL:
        """
        Wraps super() as a subquery (update-safe) then adds:
        - analytic_account display name when show_analytic_account is on
        - LATERAL rate join and per-line conversion when secondary_currency_id is set

        Both features are independent and can be combined.
        If neither is active, super() is returned directly (no overhead).
        """
        has_secondary_currency = bool(options.get('secondary_currency_id'))
        has_analytic_column    = bool(options.get('show_analytic_account'))
        has_company_column     = bool(options.get('show_company_column'))

        if not has_secondary_currency and not has_analytic_column and not has_company_column:
            return super()._get_query_amls(report, options, expanded_account_ids, offset=offset, limit=limit)

        base_query = super()._get_query_amls(
            report, options, expanded_account_ids,
            offset=0, limit=None,
        )

        # analytic JOIN — needed in FROM clause regardless of select position
        analytic_join = SQL("")
        if has_analytic_column:
            analytic_join = SQL(
                """
                LEFT JOIN account_move_line _analytic_aml ON _analytic_aml.id = base.id
                LEFT JOIN account_analytic_account _analytic_acc
                       ON _analytic_acc.id = _analytic_aml.analytic_account_id
                """
            )

        # Build extra SELECT columns as a list then join with commas.
        # This avoids any trailing/leading comma issues regardless of which
        # combination of features is active.
        extra_selects = []

        if has_analytic_column:
            lang = self.env.lang or 'en_US'
            extra_selects.append(SQL(
                """
                COALESCE(
                    _analytic_acc.name->>%(lang)s,
                    _analytic_acc.name->>'en_US'
                ) AS analytic_account
                """,
                lang=lang,
            ))

        if has_company_column:
            extra_selects.append(SQL(
                "(SELECT COALESCE(name->>'en_US', name::text) FROM res_company WHERE id = base.company_id) AS company_name"
            ))

        extra_selects_joined = SQL(", ").join(extra_selects) if extra_selects else SQL("")

        # Build the full SELECT list using named parameters only (SQL() doesn't
        # allow mixing positional %s and named %(key)s arguments).
        if has_secondary_currency:
            if extra_selects:
                outer = SQL(
                    """
                    SELECT
                        base.*,
                        %(extra_cols)s,
                        %(debit_select)s   AS debit,
                        %(credit_select)s  AS credit,
                        %(balance_select)s AS balance
                    FROM (%(base_query)s) base
                    %(analytic_join)s
                    %(lateral_rate_join)s
                    """,
                    extra_cols=extra_selects_joined,
                    base_query=base_query,
                    analytic_join=analytic_join,
                    lateral_rate_join=report._get_lateral_rate_sql(options, aml_alias='base'),
                    debit_select=report._get_secondary_currency_debit(options, aml_alias='base'),
                    credit_select=report._get_secondary_currency_credit(options, aml_alias='base'),
                    balance_select=report._get_secondary_currency_balance(options, aml_alias='base'),
                )
            else:
                outer = SQL(
                    """
                    SELECT
                        base.*,
                        %(debit_select)s   AS debit,
                        %(credit_select)s  AS credit,
                        %(balance_select)s AS balance
                    FROM (%(base_query)s) base
                    %(analytic_join)s
                    %(lateral_rate_join)s
                    """,
                    base_query=base_query,
                    analytic_join=analytic_join,
                    lateral_rate_join=report._get_lateral_rate_sql(options, aml_alias='base'),
                    debit_select=report._get_secondary_currency_debit(options, aml_alias='base'),
                    credit_select=report._get_secondary_currency_credit(options, aml_alias='base'),
                    balance_select=report._get_secondary_currency_balance(options, aml_alias='base'),
                )
        else:
            if extra_selects:
                outer = SQL(
                    """
                    SELECT
                        base.*,
                        %(extra_cols)s
                    FROM (%(base_query)s) base
                    %(analytic_join)s
                    """,
                    extra_cols=extra_selects_joined,
                    base_query=base_query,
                    analytic_join=analytic_join,
                )
            else:
                # Should not reach here (guarded above), but safe fallback
                return super()._get_query_amls(report, options, expanded_account_ids, offset=offset, limit=limit)

        if offset:
            outer = SQL('%s OFFSET %s', outer, offset)
        if limit:
            outer = SQL('%s LIMIT %s', outer, limit)

        return outer

    def _get_query_sums(self, report, options) -> SQL:
        """
        Full override to apply per-line historical rate conversion before SUM().

        Also handles hide_initial_balance: when active, delegates to
        _get_query_sums_hide_initial_balance which uses CASE WHEN date filtering
        instead of the normal from_beginning scope.

        When both secondary_currency_id and hide_initial_balance are active,
        hide_initial_balance takes priority (it must control the date scoping
        before any currency conversion).
        """
        if options.get('hide_initial_balance'):
            return self._get_query_sums_hide_initial_balance(report, options)

        if not options.get('secondary_currency_id'):
            return super()._get_query_sums(report, options)

        options_by_column_group = report._split_options_per_column_group(options)
        queries = []

        for column_group_key, options_group in options_by_column_group.items():

            # ── 1) Account sums ───────────────────────────────────────────────
            sum_date_scope = 'strict_range' if options_group.get('general_ledger_strict_range') else 'from_beginning'

            query_domain = []
            if not options_group.get('general_ledger_strict_range'):
                date_from = fields.Date.from_string(options_group['date']['date_from'])
                fy_dates = self.env.company.compute_fiscalyear_dates(date_from)
                query_domain += [
                    '|',
                    ('date', '>=', fy_dates['date_from']),
                    ('account_id.include_initial_balance', '=', True),
                ]
            if options_group.get('export_mode') == 'print' and options_group.get('filter_search_bar'):
                query_domain.append(('account_id', 'ilike', options_group['filter_search_bar']))
            if options_group.get('include_current_year_in_unaff_earnings'):
                query_domain += [('account_id.include_initial_balance', '=', True)]

            query = report._get_report_query(options_group, sum_date_scope, domain=query_domain)
            queries.append(SQL(
                """
                SELECT
                    account_move_line.account_id                            AS groupby,
                    'sum'                                                   AS key,
                    MAX(account_move_line.date)                             AS max_date,
                    %(column_group_key)s                                    AS column_group_key,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                    COALESCE(SUM(%(debit_select)s), 0.0)                    AS debit,
                    COALESCE(SUM(%(credit_select)s), 0.0)                   AS credit,
                    COALESCE(SUM(%(balance_select)s), 0.0)                  AS balance
                FROM %(table_references)s
                %(currency_table_join)s
                %(lateral_rate_join)s
                WHERE %(search_condition)s
                GROUP BY account_move_line.account_id
                """,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(options_group),
                lateral_rate_join=report._get_lateral_rate_sql(options_group),
                debit_select=report._get_secondary_currency_debit(options_group),
                credit_select=report._get_secondary_currency_credit(options_group),
                balance_select=report._get_secondary_currency_balance(options_group),
                search_condition=query.where_clause,
            ))

            # ── 2) Unaffected earnings ────────────────────────────────────────
            if not options_group.get('general_ledger_strict_range'):
                unaff_domain = [('account_id.include_initial_balance', '=', False)]
                new_options = self._get_options_unaffected_earnings(options_group)
                query = report._get_report_query(new_options, 'strict_range', domain=unaff_domain)
                queries.append(SQL(
                    """
                    SELECT
                        account_move_line.company_id                            AS groupby,
                        'unaffected_earnings'                                   AS key,
                        NULL                                                    AS max_date,
                        %(column_group_key)s                                    AS column_group_key,
                        COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                        COALESCE(SUM(%(debit_select)s), 0.0)                    AS debit,
                        COALESCE(SUM(%(credit_select)s), 0.0)                   AS credit,
                        COALESCE(SUM(%(balance_select)s), 0.0)                  AS balance
                    FROM %(table_references)s
                    %(currency_table_join)s
                    %(lateral_rate_join)s
                    WHERE %(search_condition)s
                    GROUP BY account_move_line.company_id
                    """,
                    column_group_key=column_group_key,
                    table_references=query.from_clause,
                    currency_table_join=report._currency_table_aml_join(options_group),
                    lateral_rate_join=report._get_lateral_rate_sql(options_group),
                    debit_select=report._get_secondary_currency_debit(options_group),
                    credit_select=report._get_secondary_currency_credit(options_group),
                    balance_select=report._get_secondary_currency_balance(options_group),
                    search_condition=query.where_clause,
                ))

        return SQL(" UNION ALL ").join(queries)



    # =========================================================================
    # SHOW COMPANY COLUMN — AML line builder (General Ledger)
    # =========================================================================

    def _get_aml_values(self, report, options, expanded_account_ids, offset=0, limit=None):
        """
        Override to show only the Label (name) in the Communication column,
        instead of Odoo's default "ref - name" combination.

        Odoo builds communication as f"{ref} - {name}" in the original method
        (account_general_ledger.py line 379-382). We call super() first to keep
        all standard logic intact, then replace communication with name only.
        """
        rslt, has_more = super()._get_aml_values(report, options, expanded_account_ids, offset=offset, limit=limit)

        for account_results in rslt.values():
            for aml_key_results in account_results.values():
                for aml_result in aml_key_results.values():
                    if aml_result:
                        aml_result['communication'] = aml_result.get('name', '')

        return rslt, has_more

    def _get_aml_line(self, report, parent_line_id, options, eval_dict, init_bal_by_col_group):
        """
        Full override to handle company_name column.
        When show_company_column is off, delegates to super() directly.
        When on, rebuilds all columns including company_name.
        Mirrors the original _get_aml_line structure exactly.
        """
        if not options.get('show_company_column'):
            return super()._get_aml_line(report, parent_line_id, options, eval_dict, init_bal_by_col_group)

        line_columns = []
        for column in options['columns']:
            col_expr_label = column['expression_label']

            if col_expr_label == 'company_name':
                company_name = ''
                for col_group in eval_dict.values():
                    company_name = col_group.get('company_name', '') or ''
                    if company_name:
                        break
                line_columns.append(report._build_column_dict(company_name, column, options=options))
                continue

            if col_expr_label == 'analytic_account':
                analytic_name = ''
                for col_group in eval_dict.values():
                    analytic_name = col_group.get('analytic_account', '') or ''
                    if analytic_name:
                        break
                line_columns.append(report._build_column_dict(analytic_name, column, options=options))
                continue

            col_value = eval_dict[column['column_group_key']].get(col_expr_label)
            col_currency = None
            if col_value is not None:
                if col_expr_label == 'amount_currency':
                    col_currency = self.env['res.currency'].browse(
                        eval_dict[column['column_group_key']]['currency_id']
                    )
                    col_value = None if col_currency == self.env.company.currency_id else col_value
                elif col_expr_label == 'balance':
                    col_value += (init_bal_by_col_group[column['column_group_key']] or 0)
            line_columns.append(report._build_column_dict(col_value, column, options=options, currency=col_currency))

        aml_id = move_name = caret_type = date = None
        for col_group in eval_dict.values():
            aml_id = col_group.get('id', '')
            if aml_id:
                caret_type = 'account.payment' if col_group.get('payment_id') else 'account.move.line'
                move_name  = col_group['move_name']
                date       = str(col_group.get('date', ''))
                break

        return {
            'id': report._get_generic_line_id('account.move.line', aml_id, parent_line_id=parent_line_id, markup=date),
            'caret_options': caret_type,
            'parent_id': parent_line_id,
            'name': move_name,
            'columns': line_columns,
            'level': 3,
        }

    # =========================================================================
    # HIDE INITIAL BALANCE — query sums
    # =========================================================================

    def _get_query_sums_hide_initial_balance(self, report, options) -> SQL:
        """
        When hide_initial_balance is active, restrict SUM()s to the exact
        selected date range via CASE WHEN, while keeping the same account
        discovery domain as the standard report so no accounts disappear.
        The unaffected_earnings query is skipped entirely (no opening balance).

        When secondary_currency_id is also active, applies the same LATERAL
        rate join and per-line conversion used by the standard _get_query_sums
        override, combined with the CASE WHEN date filter.
        """
        has_secondary_currency = bool(options.get('secondary_currency_id'))
        options_by_column_group = report._split_options_per_column_group(options)
        queries = []

        for column_group_key, options_group in options_by_column_group.items():
            date_from = options_group['date']['date_from']
            date_to   = options_group['date']['date_to']

            current_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(
                fields.Date.from_string(date_from)
            )

            query_domain = [
                '|',
                ('date', '>=', current_fiscalyear_dates['date_from']),
                ('account_id.include_initial_balance', '=', True),
            ]

            query = report._get_report_query(options_group, 'from_beginning', domain=query_domain)

            in_period = SQL(
                "account_move_line.date BETWEEN %(date_from)s AND %(date_to)s",
                date_from=date_from,
                date_to=date_to,
            )

            if has_secondary_currency:
                debit_select   = report._get_secondary_currency_debit(options_group)
                credit_select  = report._get_secondary_currency_credit(options_group)
                balance_select = report._get_secondary_currency_balance(options_group)
                currency_join  = report._get_lateral_rate_sql(options_group)
            else:
                debit_select   = report._currency_table_apply_rate(SQL("account_move_line.debit"))
                credit_select  = report._currency_table_apply_rate(SQL("account_move_line.credit"))
                balance_select = report._currency_table_apply_rate(SQL("account_move_line.balance"))
                currency_join  = SQL("")

            queries.append(SQL(
                """
                SELECT
                    account_move_line.account_id                                                                    AS groupby,
                    'sum'                                                                                            AS key,
                    MAX(account_move_line.date)                                                                     AS max_date,
                    %(column_group_key)s                                                                            AS column_group_key,
                    COALESCE(SUM(CASE WHEN %(in_period)s THEN account_move_line.amount_currency ELSE 0 END), 0.0) AS amount_currency,
                    COALESCE(SUM(CASE WHEN %(in_period)s THEN %(debit_select)s   ELSE 0 END), 0.0)               AS debit,
                    COALESCE(SUM(CASE WHEN %(in_period)s THEN %(credit_select)s  ELSE 0 END), 0.0)               AS credit,
                    COALESCE(SUM(CASE WHEN %(in_period)s THEN %(balance_select)s ELSE 0 END), 0.0)               AS balance
                FROM %(table_references)s
                %(currency_table_join)s
                %(lateral_rate_join)s
                WHERE %(search_condition)s
                GROUP BY account_move_line.account_id
                """,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(options_group),
                lateral_rate_join=currency_join,
                debit_select=debit_select,
                credit_select=credit_select,
                balance_select=balance_select,
                in_period=in_period,
                search_condition=query.where_clause,
            ))

        return SQL(" UNION ALL ").join(queries)

    # =========================================================================
    # HIDE INITIAL BALANCE — expand move lines
    # =========================================================================

    def _report_expand_unfoldable_line_general_ledger(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """
        When hide_initial_balance is active, skip the Initial Balance line and
        seed the running balance at 0 so move-line balances reflect only the
        selected period.
        For all other cases, delegates to super() unchanged.
        """
        from odoo.exceptions import UserError

        if not options.get('hide_initial_balance'):
            return super()._report_expand_unfoldable_line_general_ledger(
                line_dict_id, groupby, options, progress, offset,
                unfold_all_batch_data=unfold_all_batch_data,
            )

        def init_load_more_progress(line_dict):
            return {
                column['column_group_key']: line_col.get('no_format', 0)
                for column, line_col in zip(options['columns'], line_dict['columns'])
                if column['expression_label'] == 'balance'
            }

        report = self.env.ref('account_reports.general_ledger_report')
        model, model_id = report._get_model_info_from_id(line_dict_id)

        if model != 'account.account':
            raise UserError(_("Wrong ID for general ledger line to expand: %s", line_dict_id))

        lines = []

        if offset == 0:
            progress = {
                column['column_group_key']: 0
                for column in options['columns']
                if column['expression_label'] == 'balance'
            }

        limit_to_load = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None
        if unfold_all_batch_data:
            aml_results = unfold_all_batch_data['aml_results'][model_id]
            has_more    = unfold_all_batch_data['has_more'].get(model_id, False)
        else:
            aml_results, has_more = self._get_aml_values(report, options, [model_id], offset=offset, limit=limit_to_load)
            aml_results = aml_results[model_id]

        next_progress = progress
        for aml_result in aml_results.values():
            new_line = self._get_aml_line(report, line_dict_id, options, aml_result, next_progress)
            lines.append(new_line)
            next_progress = init_load_more_progress(new_line)

        return {
            'lines': lines,
            'offset_increment': report.load_more_limit,
            'has_more': has_more,
            'progress': next_progress,
        }



class PartnerLedgerEnhancedHandler(models.AbstractModel):
    """
    Consolidated Partner Ledger enhancements:

    1. Show Company Column   — adds company_name column via _get_additional_column_aml_values() hook
    2. Show Analytic Account — adds analytic_account column via same hook
    3. Hide Initial Balance  — skips Initial Balance line, resets running balance to 0
    4. Communication fix     — shows Label (name) only, not "ref - name" combined string

    All features are independent and can be combined freely.
    """
    _inherit = 'account.partner.ledger.report.handler'

    # =========================================================================
    # OPTIONS
    # =========================================================================

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        # ── Show Company column ───────────────────────────────────────────────
        options['show_company_column'] = (previous_options or {}).get('show_company_column', False)
        if not options['show_company_column']:
            options['columns'] = [
                col for col in options['columns']
                if col['expression_label'] != 'company_name'
            ]

        # ── Show Analytic Account column ──────────────────────────────────────
        options['show_analytic_account'] = (previous_options or {}).get('show_analytic_account', False)
        if not options['show_analytic_account']:
            options['columns'] = [
                col for col in options['columns']
                if col['expression_label'] != 'analytic_account'
            ]

        # ── Hide Initial Balance ───────────────────────────────────────────────
        options['hide_initial_balance'] = (previous_options or {}).get('hide_initial_balance', False)

    # =========================================================================
    # SQL — additional AML columns via Odoo hook
    # =========================================================================

    def _get_additional_column_aml_values(self):
        """
        Uses the native hook to inject extra columns into the AML query.
        Each column is only added when its toggle is active.
        analytic_account_id is a stored field on account_move_line (this module).
        company_name uses a correlated subquery on the tiny res_company table.
        """
        parts = []

        if self.env.context.get('show_company_column'):
            parts.append(SQL(
                "(SELECT COALESCE(name->>'en_US', name::text) FROM res_company WHERE id = account_move_line.company_id) AS company_name,"
            ))

        if self.env.context.get('show_analytic_account'):
            lang = self.env.lang or 'en_US'
            parts.append(SQL(
                """
                (
                    SELECT COALESCE(aa.name->>%(lang)s, aa.name->>'en_US')
                    FROM account_analytic_account aa
                    WHERE aa.id = account_move_line.analytic_account_id
                ) AS analytic_account,
                """,
                lang=lang,
            ))

        return SQL("").join(parts) if parts else SQL("")

    # =========================================================================
    # AML line builder — handles all extra columns + communication fix
    # =========================================================================

    def _get_report_line_move_line(self, options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift=0):
        """
        Full override: handles company_name, analytic_account extra columns,
        and replaces the default _format_aml_name (ref - name) with name-only
        for the Communication column.

        When none of our features are active, delegates to super() to avoid
        any risk of regression on the standard Partner Ledger.
        """
        caret_type = 'account.payment' if aml_query_result['payment_id'] else 'account.move.line'
        columns = []
        report = self.env['account.report'].browse(options['report_id'])

        for column in options['columns']:
            col_expr_label = column['expression_label']

            # Extra columns — safe .get() since they may not be in aml_query_result
            # when their toggle is off (SQL hook didn't inject them)
            if col_expr_label == 'company_name':
                val = aml_query_result.get('company_name', '') or ''
                columns.append(report._build_column_dict(val, column, options=options))
                continue

            if col_expr_label == 'analytic_account':
                val = aml_query_result.get('analytic_account', '') or ''
                columns.append(report._build_column_dict(val, column, options=options))
                continue

            col_value = aml_query_result.get(col_expr_label) if column['column_group_key'] == aml_query_result['column_group_key'] else None
            if col_value is None:
                columns.append(report._build_column_dict(None, None))
            else:
                currency = False
                if col_expr_label == 'balance':
                    col_value += init_bal_by_col_group[column['column_group_key']]
                if col_expr_label == 'amount_currency':
                    currency = self.env['res.currency'].browse(aml_query_result['currency_id'])
                    if currency == self.env.company.currency_id:
                        col_value = ''
                columns.append(report._build_column_dict(col_value, column, options=options, currency=currency))

        return {
            'id': report._get_generic_line_id(
                'account.move.line', aml_query_result['id'],
                parent_line_id=partner_line_id,
                markup=aml_query_result['partial_id'],
            ),
            'parent_id': partner_line_id,
            # Communication fix: show Label (name) only, not "ref - name"
            'name': aml_query_result.get('name') or aml_query_result.get('move_name', ''),
            'columns': columns,
            'caret_options': caret_type,
            'level': 3 + level_shift,
        }

    # =========================================================================
    # AML query — pass options to context for _get_additional_column_aml_values
    # =========================================================================

    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        """
        Passes show_company_column and show_analytic_account to context so that
        _get_additional_column_aml_values() (called inside the super query) can
        inject the correct extra SQL columns based on current options.
        """
        ctx = {}
        if options.get('show_company_column'):
            ctx['show_company_column'] = True
        if options.get('show_analytic_account'):
            ctx['show_analytic_account'] = True

        if ctx:
            # Must use explicit class in super() to avoid infinite recursion —
            # with_context() returns a new recordset of the same class, so a plain
            # super() call would resolve back to this method again.
            return super(PartnerLedgerEnhancedHandler, self.with_context(**ctx))._get_aml_values(
                options, partner_ids, offset=offset, limit=limit
            )
        return super()._get_aml_values(options, partner_ids, offset=offset, limit=limit)

    # =========================================================================
    # Hide Initial Balance — expand override
    # =========================================================================

    def _report_expand_unfoldable_line_partner_ledger(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """
        When hide_initial_balance is active, skip the Initial Balance line
        and seed the running balance at 0 for the selected period only.
        Otherwise delegates to super() unchanged.
        """
        if not options.get('hide_initial_balance'):
            return super()._report_expand_unfoldable_line_partner_ledger(
                line_dict_id, groupby, options, progress, offset,
                unfold_all_batch_data=unfold_all_batch_data,
            )

        def init_load_more_progress(line_dict):
            return {
                column['column_group_key']: line_col.get('no_format', 0)
                for column, line_col in zip(options['columns'], line_dict['columns'])
                if column['expression_label'] == 'balance'
            }

        report = self.env.ref('account_reports.partner_ledger_report')
        markup, model, record_id = report._parse_line_id(line_dict_id)[-1]

        if model != 'res.partner':
            raise UserError(_("Wrong ID for partner ledger line to expand: %s", line_dict_id))

        prefix_groups_count = sum(
            1 for m, _, _ in report._parse_line_id(line_dict_id)
            if isinstance(m, dict) and 'groupby_prefix_group' in m
        )
        level_shift = prefix_groups_count * 2

        lines = []

        if offset == 0:
            # Skip Initial Balance — seed progress at 0
            progress = {
                column['column_group_key']: 0
                for column in options['columns']
                if column['expression_label'] == 'balance'
            }

        limit_to_load = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None

        if unfold_all_batch_data:
            aml_results = unfold_all_batch_data['aml_values'][record_id]
        else:
            aml_results = self._get_aml_values(options, [record_id], offset=offset, limit=limit_to_load)[record_id]

        has_more = False
        treated_results_count = 0
        next_progress = progress
        for result in aml_results:
            if options['export_mode'] != 'print' and report.load_more_limit and treated_results_count == report.load_more_limit:
                has_more = True
                break
            new_line = self._get_report_line_move_line(options, result, line_dict_id, next_progress, level_shift=level_shift)
            lines.append(new_line)
            next_progress = init_load_more_progress(new_line)
            treated_results_count += 1

        return {
            'lines': lines,
            'offset_increment': treated_results_count,
            'has_more': has_more,
            'progress': next_progress,
        }


class PartnerLedgerCustomHandlerHideZero(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        """
        Inject hide_zero_balance into Partner Ledger options.

        Partner Ledger uses _custom_options_initializer (not the _init_options_*
        prefix convention), and has no hide_0_lines in its options.
        So _init_options_hide_zero_balance alone is not enough — we must also
        add hide_zero_balance here so it appears in options before the frontend
        renders and before _build_partner_lines checks it.
        """
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        if not report.filter_hide_zero_balance:
            return

        options['hide_zero_balance'] = (previous_options or {}).get('hide_zero_balance', False)

    def _build_partner_lines(self, report, options, level_shift=0):
        """
        Filter out partners whose balance = 0 across all column groups
        when hide_zero_balance is active.
        """
        lines, totals_by_column_group = super()._build_partner_lines(
            report, options, level_shift=level_shift,
        )

        if not options.get('hide_zero_balance'):
            return lines, totals_by_column_group

        company_currency = self.env.company.currency_id

        filtered_lines = []
        for line in lines:
            balance_values = [
                col.get('no_format', 0) or 0
                for col, col_def in zip(line['columns'], options['columns'])
                if col_def['expression_label'] == 'balance'
            ]
            if any(not company_currency.is_zero(b) for b in balance_values):
                filtered_lines.append(line)

        return filtered_lines, totals_by_column_group


class TrialBalanceCustomHandler(models.AbstractModel):
    _inherit = 'account.trial.balance.report.handler'

    # =========================================================================
    # OPTIONS
    # =========================================================================

    def _custom_options_initializer(self, report, options, previous_options):
        """
        Adds two new options to Trial Balance:
        - hide_initial_balance : removes Initial Balance columns from the report
        - group_by_company     : groups account rows under their company

        hide_initial_balance must be processed BEFORE calling super() because
        super() (_custom_options_initializer on TrialBalanceCustomHandler core)
        builds and injects the Initial Balance column group. We flag it here and
        act on it in _dynamic_lines_generator / by filtering options['columns'].

        group_by_company is injected here so the Custom dropdown JS can see it
        in controller.options; actual grouping is done in _dynamic_lines_generator.
        """
        # Store our options before super() adds Initial Balance columns
        hide_ib = (previous_options or {}).get('hide_initial_balance', False)
        group_co = (previous_options or {}).get('group_by_company', False)

        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options['hide_initial_balance'] = hide_ib
        options['group_by_company']     = group_co

        # Remove Initial Balance columns/group if hide_initial_balance is on.
        # super() already injected them — we strip them out here.
        if hide_ib:
            from odoo.addons.account_reports.models.account_trial_balance_report import TRIAL_BALANCE_END_COLUMN_GROUP_KEY
            ib_group_keys = {
                key for key, grp in options['column_groups'].items()
                if key != TRIAL_BALANCE_END_COLUMN_GROUP_KEY
                and grp.get('forced_options', {}).get('date', {}).get('date_from') is None
                and 'include_current_year_in_unaff_earnings' in grp.get('forced_options', {})
            }
            # Simpler: detect by column expression_label — Initial Balance columns
            # are the ones that share expression_label with the middle period but
            # belong to a different column_group_key. We identify the IB group key
            # as the one whose forced_options includes include_current_year_in_unaff_earnings.
            ib_col_group_keys = {
                col['column_group_key'] for col in options['columns']
                if options['column_groups'].get(col['column_group_key'], {})
                    .get('forced_options', {}).get('include_current_year_in_unaff_earnings') is not None
                and col['column_group_key'] != TRIAL_BALANCE_END_COLUMN_GROUP_KEY
            }
            if ib_col_group_keys:
                # Remove IB columns and their column_groups
                options['columns'] = [
                    col for col in options['columns']
                    if col['column_group_key'] not in ib_col_group_keys
                ]
                for key in ib_col_group_keys:
                    options['column_groups'].pop(key, None)

    # =========================================================================
    # DYNAMIC LINES
    # =========================================================================

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        """
        Handles three features on top of the standard Trial Balance:

        1. hide_zero_balance    — strips accounts with zero End Balance
        2. hide_initial_balance — Initial Balance columns already removed by
                                  _custom_options_initializer; nothing extra needed here
        3. group_by_company     — wraps account rows under collapsible Company headers
                                  with per-company debit/credit totals

        Order: get lines from super() → apply hide_zero_balance → apply group_by_company.
        """
        from odoo.addons.account_reports.models.account_trial_balance_report import TRIAL_BALANCE_END_COLUMN_GROUP_KEY

        # Temporarily remove options that affect GL internals but shouldn't
        # when TB calls GL._dynamic_lines_generator internally.
        # TB handles hide_initial_balance by stripping columns (done in
        # _custom_options_initializer), not by GL's query-level logic.
        # group_by_company on GL would restructure the output in a way TB
        # can't process — TB does its own grouping after getting flat rows.
        clean_options = {
            **options,
            'hide_initial_balance': False,
            'group_by_company':     False,
            'group_by_analytic':    False,
        }

        lines = super()._dynamic_lines_generator(
            report, clean_options, all_column_groups_expression_totals, warnings=warnings
        )

        # ── 1. Hide Zero Balance ──────────────────────────────────────────────
        if options.get('hide_zero_balance'):
            currency = self.env.company.currency_id
            end_debit_index = next((
                i for i, col in enumerate(options['columns'])
                if col.get('expression_label') == 'debit'
                and col.get('column_group_key') == TRIAL_BALANCE_END_COLUMN_GROUP_KEY
            ), None)
            end_credit_index = next((
                i for i, col in enumerate(options['columns'])
                if col.get('expression_label') == 'credit'
                and col.get('column_group_key') == TRIAL_BALANCE_END_COLUMN_GROUP_KEY
            ), None)

            filtered = []
            for sequence, line in lines:
                model = report._get_model_info_from_id(line['id'])[0]
                if model != 'account.account':
                    filtered.append((sequence, line))
                    continue
                end_debit  = (line['columns'][end_debit_index]['no_format']  if end_debit_index  is not None else 0.0) or 0.0
                end_credit = (line['columns'][end_credit_index]['no_format'] if end_credit_index is not None else 0.0) or 0.0
                if not currency.is_zero(end_debit) or not currency.is_zero(end_credit):
                    filtered.append((sequence, line))
            lines = filtered

        # ── 2. Group by Company ───────────────────────────────────────────────
        if not options.get('group_by_company'):
            return lines

        # Separate account lines from grand total
        account_lines = [(s, l) for s, l in lines if report._get_model_info_from_id(l['id'])[0] == 'account.account']
        other_lines   = [(s, l) for s, l in lines if report._get_model_info_from_id(l['id'])[0] != 'account.account']

        # In Odoo 18, account.account has company_ids (Many2many), not company_id.
        # We determine each line's company from account_move_line via a single
        # aggregate query: for each account_id, find which company_ids posted
        # to it within the current report domain.
        account_ids = [report._get_model_info_from_id(l['id'])[1] for _, l in account_lines]

        account_company_map = {}  # {account_id: company_id}
        if account_ids:
            query = report._get_report_query(options, 'from_beginning')
            self._cr.execute(SQL(
                """
                SELECT DISTINCT ON (account_move_line.account_id)
                    account_move_line.account_id,
                    account_move_line.company_id
                FROM %(table_references)s
                WHERE %(search_condition)s
                  AND account_move_line.account_id = ANY(%(account_ids)s)
                ORDER BY account_move_line.account_id, account_move_line.company_id
                """,
                table_references=query.from_clause,
                search_condition=query.where_clause,
                account_ids=account_ids,
            ))
            for row in self._cr.dictfetchall():
                account_company_map[row['account_id']] = row['company_id']

        # Group account lines by company
        from collections import defaultdict
        company_groups = defaultdict(list)
        for seq, line in account_lines:
            acc_id = report._get_model_info_from_id(line['id'])[1]
            cid = account_company_map.get(acc_id)
            company_groups[cid].append((seq, line))

        # Fetch company records in one browse
        company_ids_list = [cid for cid in company_groups if cid]
        companies = {c.id: c for c in self.env['res.company'].browse(company_ids_list)}

        result = []
        n_cols = len(options['columns'])

        for cid, grp_lines in company_groups.items():
            company = companies.get(cid)
            company_name = company.display_name if company else _("Unknown Company")

            # Per-company totals: sum every numeric column
            totals = [0.0] * n_cols
            for _seq, l in grp_lines:
                for i, col in enumerate(l['columns']):
                    val = col.get('no_format') or 0.0
                    if isinstance(val, (int, float)):
                        totals[i] += val

            company_columns = [
                report._build_column_dict(totals[i], options['columns'][i], options=options)
                for i in range(n_cols)
            ]

            company_line_id = report._get_generic_line_id('res.company', cid)
            result.append((0, {
                'id':          company_line_id,
                'name':        company_name,
                'columns':     company_columns,
                'level':       1,
                'unfoldable':  True,
                'unfolded':    any(
                    report._get_res_id_from_line_id(lid, 'res.company') == cid
                    for lid in options.get('unfolded_lines', [])
                ) or options.get('unfold_all', False),
                'expand_function': '_report_expand_unfoldable_line_tb_company',
            }))

            for seq, line in grp_lines:
                child = dict(line)
                child['parent_id'] = company_line_id
                child['level']     = 2
                child['id']        = report._build_subline_id(company_line_id, line['id'])
                result.append((seq, child))

        result.extend(other_lines)
        return result

    def _report_expand_unfoldable_line_tb_company(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """
        Called when the user expands a Company row in the grouped Trial Balance.
        Re-generates TB scoped to this company via forced_domain and returns
        its account rows.
        """
        report = self.env.ref('account_reports.trial_balance_report')
        company_id = report._get_res_id_from_line_id(line_dict_id, 'res.company')

        if not company_id:
            return {'lines': [], 'offset_increment': 0, 'has_more': False}

        scoped_options = {
            **options,
            'forced_domain': options.get('forced_domain', []) + [('company_id', '=', company_id)],
            'group_by_company': False,
        }

        all_column_groups_expression_totals = {}
        all_lines = super()._dynamic_lines_generator(
            report, scoped_options, all_column_groups_expression_totals
        )

        child_lines = []
        for _, line in all_lines:
            acc_model, acc_id = report._get_model_info_from_id(line['id'])
            if acc_model == 'account.account':
                child = dict(line)
                child['parent_id'] = line_dict_id
                child['level']     = 2
                child['id']        = report._build_subline_id(line_dict_id, line['id'])
                child_lines.append(child)

        return {'lines': child_lines, 'offset_increment': len(child_lines), 'has_more': False}