from odoo import models, fields, api
from odoo.tools.sql import SQL
from odoo.tools.query import Query
import logging
_logger = logging.getLogger(__name__)


class SaleCommissionAchievementApproval(models.Model):
    _name = 'sale.commission.achievement.approval'
    _description = 'Track Approvals of Commission Report'

    report_related_res_id = fields.Integer(string="Related Record ID", required=True)
    report_related_res_model = fields.Char(string="Related Model", required=True)
    approved_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    approved_date = fields.Datetime(default=fields.Datetime.now)


class SaleCommissionAchievementSnapshot(models.Model):
    _name = 'sale.commission.achievement.snapshot'
    _description = 'Frozen copy of approved commission report'
    _order = 'date DESC, plan_id'
    _rec_name = 'related_res_id'

    target_id = fields.Many2one('sale.commission.plan.target', "Period", readonly=True)
    plan_id = fields.Many2one('sale.commission.plan', "Commission Plan", readonly=True)
    user_id = fields.Many2one('res.users', "Sales Person", readonly=True)
    team_id = fields.Many2one('crm.team', "Sales Team", readonly=True)
    achieved = fields.Monetary("Achieved", readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', "Currency", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    date = fields.Date(string="Date", readonly=True)

    related_res_model = fields.Char(readonly=True)
    related_res_id = fields.Integer(readonly=True)
    invoice_name = fields.Char(string="Customer Invoice", readonly=True)
    invoice_amount_signed = fields.Monetary(string="Invoice Total", currency_field='currency_id', readonly=True)
    invoice_partner_display_name = fields.Char(string="Customer", readonly=True)
    invoice_additional_salespersons = fields.Char(string="Co-Sales Person", readonly=True)
    invoice_additional_salespersons_companies = fields.Char(string="Additional Salesperson's Branch", readonly=True)
    invoice_paid_amount = fields.Monetary(string="Paid Amount", currency_field='currency_id', readonly=True)
    third_party_deduction = fields.Monetary(string="Third-Party Deduction", currency_field='currency_id', readonly=True)
    tax_deduction = fields.Monetary(string="Tax Deduction", currency_field='currency_id', readonly=True)
    net_paid = fields.Monetary(string="Net Paid", currency_field='currency_id', readonly=True)
    net_paid_after_split = fields.Monetary(string="Net Paid (After Split)", currency_field='currency_id', readonly=True)
    is_approved = fields.Boolean(default=True, readonly=True)


class SaleAchievementReport(models.Model):
    _inherit = "sale.commission.achievement.report"

    invoice_amount_signed = fields.Monetary(
        string="Invoice Total",
        readonly=True,
        currency_field='currency_id',
    )
    invoice_partner_display_name = fields.Char(
        string="Customer",
        readonly=True
    )
    invoice_additional_salespersons = fields.Char(
        string="Co-Sales Person",
        readonly=True
    )
    invoice_additional_salespersons_companies = fields.Char(
        string="Additional Salesperon's Branch",
        readonly=True
    )
    invoice_paid_amount = fields.Monetary(
        string="Paid Amount",
        readonly=True,
        currency_field='currency_id'
    )
    third_party_deduction = fields.Monetary(
        string="Third-Party Deduction",
        readonly=True,
        currency_field='currency_id'
    )
    tax_deduction = fields.Monetary(
        string="Tax Deduction",
        readonly=True,
        currency_field='currency_id'
    )
    net_paid = fields.Monetary(
        string="Net Paid",
        readonly=True,
        currency_field='currency_id'
    )
    net_paid_after_split = fields.Monetary(
        string="Net Paid (After Split)",
        readonly=True,
        currency_field='currency_id',
        help="Net Paid divided equally among all salespersons on the invoice (primary + additional).",
    )

    invoice_name = fields.Char(
        string="Customer Invoice",
        readonly=True,
    )
    is_approved = fields.Boolean(string="Approved", readonly=True, default=False)

    _COMMISSION_VIEW_FIELDS = (
        "user_id, team_id, plan_id, achieved, currency_id, date, company_id, "
        "related_res_id, invoice_name, "
        "invoice_amount_signed, invoice_partner_display_name, "
        "invoice_additional_salespersons, invoice_additional_salespersons_companies, "
        "invoice_paid_amount, third_party_deduction, tax_deduction, net_paid, "
        "net_paid_after_split, "
        "is_approved, "
        "related_res_model"
    )

    def _notify(self, title, message, sticky=False, type='info'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': sticky,
                'type': type,
            }
        }

    def action_approve(self):
        """Approve only not-yet-approved rows; skip the rest. Then reload."""
        unapproved = self.filtered(lambda r: not r.is_approved)

        if not unapproved:
            # Everything selected is already approved -> notify only
            return self._notify('Nothing to do', 'All selected rows are already approved.', type='warning')

        # Use your existing approve logic but apply it only to 'unapproved'
        Approval = self.env['sale.commission.achievement.approval'].sudo()
        Snapshot = self.env['sale.commission.achievement.snapshot'].sudo()
        Target = self.env['sale.commission.plan.target']

        # Read once to avoid lazy fields during create
        data = unapproved.read([
            'plan_id', 'user_id', 'team_id', 'achieved', 'currency_id', 'date', 'company_id',
            'related_res_id', 'related_res_model',
            'invoice_name', 'invoice_amount_signed', 'invoice_partner_display_name',
            'invoice_additional_salespersons', 'invoice_additional_salespersons_companies',
            'invoice_paid_amount', 'third_party_deduction', 'tax_deduction',
            'net_paid', 'net_paid_after_split'
        ])

        # Create snapshots + approvals
        created = 0
        for vals in data:
            # find period
            target = Target.search([
                ('plan_id', '=', vals['plan_id'][0] if vals['plan_id'] else False),
                ('date_from', '<=', vals['date']),
                ('date_to', '>=', vals['date']),
            ], limit=1)

            # avoid duplicate approvals for the same doc
            appr_domain = [
                ('report_related_res_id', '=', vals['related_res_id']),
                ('report_related_res_model', '=', vals['related_res_model']),
            ]
            if Approval.search_count(appr_domain):
                continue

            # snapshot
            Snapshot.create({
                'target_id': target.id if target else False,
                'plan_id': vals['plan_id'][0] if vals['plan_id'] else False,
                'user_id': vals['user_id'][0] if vals['user_id'] else False,
                'team_id': vals['team_id'][0] if vals['team_id'] else False,
                'achieved': vals['achieved'],
                'currency_id': vals['currency_id'][0] if vals['currency_id'] else False,
                'company_id': vals['company_id'][0] if vals['company_id'] else False,
                'date': vals['date'],
                'related_res_model': vals['related_res_model'],
                'related_res_id': vals['related_res_id'],
                'invoice_name': vals['invoice_name'],
                'invoice_amount_signed': vals['invoice_amount_signed'],
                'invoice_partner_display_name': vals['invoice_partner_display_name'],
                'invoice_additional_salespersons': vals['invoice_additional_salespersons'],
                'invoice_additional_salespersons_companies': vals['invoice_additional_salespersons_companies'],
                'invoice_paid_amount': vals['invoice_paid_amount'],
                'third_party_deduction': vals['third_party_deduction'],
                'tax_deduction': vals['tax_deduction'],
                'net_paid': vals['net_paid'],
                'net_paid_after_split': vals['net_paid_after_split'],
                'is_approved': True,
            })

            # approval marker (one per document)
            Approval.create(appr_domain[0] | appr_domain[1] if False else {
                'report_related_res_id': vals['related_res_id'],
                'report_related_res_model': vals['related_res_model'],
            })
            created += 1

        # Reload and notify
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'menu_id': self.env.context.get('menu_id'),
                'action': self.env.context.get('action'),
                'next': self._notify('Approved', f'{created} row(s) approved.').get('params')
            }
        }

    def action_unapprove(self):
        """Unapprove only already-approved rows; skip others. Then reload."""
        approved = self.filtered(lambda r: r.is_approved)

        if not approved:
            return self._notify('Nothing to do', 'No approved rows in your selection.', type='warning')

        Approval = self.env['sale.commission.achievement.approval'].sudo()
        Snapshot = self.env['sale.commission.achievement.snapshot'].sudo()

        rows = approved.read(['related_res_id', 'related_res_model'])
        pairs = {(r['related_res_id'], r['related_res_model']) for r in rows}

        removed_docs = 0
        for related_res_id, related_res_model in pairs:
            # delete frozen rows (all snapshots for that doc)
            Snapshot.search([
                ('related_res_id', '=', related_res_id),
                ('related_res_model', '=', related_res_model),
            ]).unlink()
            # delete approval flag
            Approval.search([
                ('report_related_res_id', '=', related_res_id),
                ('report_related_res_model', '=', related_res_model),
            ]).unlink()
            removed_docs += 1

        # Reload and notify
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'menu_id': self.env.context.get('menu_id'),
                'action': self.env.context.get('action'),
                'next': self._notify('Approval removed', f'{removed_docs} document(s) unapproved.').get('params')
            }
        }

    @property
    def _table_query(self):
        users = self.env.context.get('commission_user_ids', [])
        if users:
            users = self.env['res.users'].browse(users).exists()
        teams = self.env.context.get('commission_team_ids', [])
        if teams:
            teams = self.env['crm.team'].browse(teams).exists()
        return f"""
WITH {self._commission_lines_query(users=users, teams=teams)}
(

    SELECT
        s.id,
        s.target_id,
        s.user_id,
        s.team_id,
        s.plan_id,
        s.achieved,
        s.currency_id,
        s.date,
        s.company_id,
        s.related_res_id,
        s.invoice_name,
        s.invoice_amount_signed,
        s.invoice_partner_display_name,
        s.invoice_additional_salespersons,
        s.invoice_additional_salespersons_companies,
        s.invoice_paid_amount,
        s.third_party_deduction,
        s.tax_deduction,
        s.net_paid,
        s.net_paid_after_split,
        s.is_approved,
        s.related_res_model
    FROM sale_commission_achievement_snapshot s

    UNION ALL


    SELECT
        ROW_NUMBER() OVER (ORDER BY cl.date DESC, cl.plan_id) + 1000000 AS id,
        era.id AS target_id,
        cl.user_id,
        cl.team_id,
        cl.plan_id,
        cl.achieved,
        cl.currency_id,
        cl.date,
        cl.company_id,
        cl.related_res_id,
        cl.invoice_name,
        cl.invoice_amount_signed,
        cl.invoice_partner_display_name,
        cl.invoice_additional_salespersons,
        cl.invoice_additional_salespersons_companies,
        cl.invoice_paid_amount,
        cl.third_party_deduction,
        cl.tax_deduction,
        cl.net_paid,
        cl.net_paid_after_split,
        FALSE AS is_approved,
        cl.related_res_model
    FROM commission_lines cl
    JOIN sale_commission_plan_target era
      ON cl.plan_id = era.plan_id
     AND cl.date BETWEEN era.date_from AND era.date_to
    WHERE NOT EXISTS (
        SELECT 1
        FROM sale_commission_achievement_approval a
        WHERE a.report_related_res_id = cl.related_res_id
          AND a.report_related_res_model = cl.related_res_model
    )
)
"""

    def _commission_lines_cte(self, users=None, teams=None):
        return [
            self._achievement_lines(users, teams),
            self._sale_lines(users, teams),
            self._invoices_lines(users, teams),
        ]

    def _commission_lines_query(self, users=None, teams=None):
        ctes = self._commission_lines_cte(users, teams)
        queries = [x[0] for x in ctes]
        table_names = [x[1] for x in ctes]
        return f"""
{','.join(queries)},
commission_lines AS (
    SELECT {self._COMMISSION_VIEW_FIELDS} FROM {table_names[0]}
    UNION ALL
    SELECT {self._COMMISSION_VIEW_FIELDS} FROM {table_names[1]}
    UNION ALL
    SELECT {self._COMMISSION_VIEW_FIELDS} FROM {table_names[2]}
)
"""

    # ---------- ACHIEVEMENT LINES ----------
    def _achievement_lines(self, users=None, teams=None):
        return f"""
achievement_commission_lines AS (
    SELECT
        sca.user_id AS user_id,
        sca.team_id AS team_id,
        scp.id AS plan_id,
        sca.currency_rate * sca.amount * scpa.rate AS achieved,
        scp.currency_id AS currency_id,
        sca.date AS date,
        scp.company_id AS company_id,
        sca.id AS related_res_id,
        NULL::varchar AS invoice_name,
        NULL::numeric AS invoice_amount_signed,
        NULL::varchar AS invoice_partner_display_name,
        NULL::varchar AS invoice_additional_salespersons,
        NULL::varchar AS invoice_additional_salespersons_companies,
        NULL::numeric AS invoice_paid_amount,
        NULL::numeric AS third_party_deduction,
        NULL::numeric AS tax_deduction,
        NULL::numeric AS net_paid,
        NULL::numeric AS net_paid_after_split,
        EXISTS (
            SELECT 1
            FROM sale_commission_achievement_approval scaa
            WHERE scaa.report_related_res_id = sca.id
              AND scaa.report_related_res_model = 'sale.commission.achievement'
        ) AS is_approved,
        'sale.commission.achievement' AS related_res_model
    FROM sale_commission_achievement sca
    JOIN sale_commission_plan scp ON scp.company_id = sca.company_id
    JOIN sale_commission_plan_achievement scpa ON scpa.plan_id = scp.id
    JOIN sale_commission_plan_user scpu ON scpu.plan_id = scp.id
    WHERE scp.active
      AND scp.state = 'approved'
      AND sca.type = scpa.type
      AND CASE WHEN scp.user_type = 'person'
               THEN sca.user_id = scpu.user_id
               ELSE sca.team_id = scp.team_id
          END
    {'AND sca.user_id IN (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
    {'AND sca.team_id IN (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
)
""", 'achievement_commission_lines'

    # ---------- SALE LINES ----------
    def _sale_lines(self, users=None, teams=None):
        return f"""
sale_rules AS (
    SELECT
        COALESCE(scpu.date_from, scp.date_from) AS date_from,
        COALESCE(scpu.date_to, scp.date_to) AS date_to,
        scpu.user_id AS user_id,
        scp.team_id AS team_id,
        scp.id AS plan_id,
        scpa.product_id,
        scpa.product_categ_id,
        scp.company_id,
        scp.currency_id,
        scp.user_type = 'team' AS team_rule,
        {self._rate_to_case(self._get_sale_rates())}
    FROM sale_commission_plan_achievement scpa
    JOIN sale_commission_plan scp ON scp.id = scpa.plan_id
    JOIN sale_commission_plan_user scpu ON scpa.plan_id = scpu.plan_id
    WHERE scp.active
      AND scp.state = 'approved'
      AND scpa.type IN ({','.join("'%s'" % r for r in self._get_sale_rates())})
    {'AND scpu.user_id IN (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
), sale_commission_lines AS (
    SELECT
        MAX(rules.user_id) AS user_id,
        MAX(so.team_id) AS team_id,
        rules.plan_id AS plan_id,
        SUM({self._get_sale_rates_product()}) AS achieved,
        MAX(rules.currency_id) AS currency_id,
        MAX(so.date_order) AS date,
        MAX(rules.company_id) AS company_id,
        so.id AS related_res_id,
        NULL::varchar AS invoice_name,
        NULL::numeric AS invoice_amount_signed,
        NULL::varchar AS invoice_partner_display_name,
        NULL::varchar AS invoice_additional_salespersons,
        NULL::varchar AS invoice_additional_salespersons_companies,
        NULL::numeric AS invoice_paid_amount,
        NULL::numeric AS third_party_deduction,
        NULL::numeric AS tax_deduction,
        NULL::numeric AS net_paid,
        NULL::numeric AS net_paid_after_split,
        EXISTS (
            SELECT 1
            FROM sale_commission_achievement_approval scaa
            WHERE scaa.report_related_res_id = so.id
              AND scaa.report_related_res_model = 'sale.order'
        ) AS is_approved,
        'sale.order' AS related_res_model
    FROM sale_rules rules
    JOIN sale_order so ON so.company_id = rules.company_id
    JOIN sale_order_line sol ON sol.order_id = so.id
    JOIN product_product pp ON sol.product_id = pp.id
    JOIN product_template pt ON pp.product_tmpl_id = pt.id
    WHERE sol.display_type IS NULL
      AND so.state = 'sale'
      AND (rules.product_id IS NULL OR rules.product_id = sol.product_id)
      AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
      AND COALESCE(sol.is_expense, false) = false
      AND COALESCE(sol.is_downpayment, false) = false
      AND so.date_order BETWEEN rules.date_from AND rules.date_to
      AND (
        (rules.team_rule AND so.team_id = rules.team_id)
        OR
        (NOT rules.team_rule AND so.user_id = rules.user_id)
      )
    {'AND so.user_id IN (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
    {'AND so.team_id IN (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
    GROUP BY so.id, rules.plan_id
)
""", 'sale_commission_lines'

    # ---------- INVOICE LINES ----------
    def _invoices_lines(self, users=None, teams=None):
        return f"""
invoices_rules AS (
    SELECT
        COALESCE(scpu.date_from, scp.date_from) AS date_from,
        COALESCE(scpu.date_to, scp.date_to) AS date_to,
        scpu.user_id AS user_id,
        scp.team_id AS team_id,
        scp.id AS plan_id,
        scpa.product_id,
        scpa.product_categ_id,
        scp.company_id,
        scp.currency_id,
        scp.user_type = 'team' AS team_rule,
        {self._rate_to_case(self._get_invoices_rates())}
    FROM sale_commission_plan_achievement scpa
    JOIN sale_commission_plan scp ON scp.id = scpa.plan_id
    JOIN sale_commission_plan_user scpu ON scpa.plan_id = scpu.plan_id
    WHERE scp.active
      AND scp.state = 'approved'
      AND scpa.type IN ({','.join("'%s'" % r for r in self._get_invoices_rates())})
    {'AND scpu.user_id IN (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
),
invoice_participants AS (
    SELECT am.id AS invoice_id, am.invoice_user_id AS user_id
    FROM account_move am
    WHERE am.move_type = 'out_invoice'
    UNION
    SELECT rel.move_id AS invoice_id, rel.user_id AS user_id
    FROM account_move_additional_user_rel rel
),
participants_per_invoice AS (
    SELECT invoice_id, COUNT(*)::int AS participants_count
    FROM invoice_participants
    GROUP BY invoice_id
),
payment_deductions_per_invoice AS (
    SELECT
        inv_am.id AS invoice_id,
        COALESCE(SUM(apr.amount * COALESCE(ded.deduction_percent/100, 0)), 0) AS third_party_deduction
    FROM account_move inv_am
    JOIN account_move_line inv_line ON inv_line.move_id = inv_am.id
    JOIN account_account inv_acc ON inv_acc.id = inv_line.account_id AND inv_acc.account_type = 'asset_receivable'
    JOIN account_partial_reconcile apr ON apr.debit_move_id = inv_line.id OR apr.credit_move_id = inv_line.id
    JOIN account_move_line pay_line ON pay_line.id = CASE
        WHEN apr.debit_move_id = inv_line.id THEN apr.credit_move_id
        ELSE apr.debit_move_id
    END
    JOIN account_move pay_move ON pay_move.id = pay_line.move_id
    JOIN account_payment pay ON pay.move_id = pay_move.id
    LEFT JOIN sale_commission_payment_method_line_deduction ded
        ON ded.payment_method_line_id = pay.payment_method_line_id AND ded.active
    WHERE inv_am.move_type = 'out_invoice'
    GROUP BY inv_am.id
),
invoice_commission_lines AS (
    SELECT
        ip.user_id AS user_id,
        MAX(am.team_id) AS team_id,
        rules.plan_id AS plan_id,
        SUM({self._get_invoice_rates_product()}) AS achieved,
        MAX(rules.currency_id) AS currency_id,
        MAX(am.date) AS date,
        MAX(rules.company_id) AS company_id,
        am.id AS related_res_id,
        MAX(am.name) AS invoice_name,
        MAX(am.amount_total_in_currency_signed) AS invoice_amount_signed,
        MAX(partner.name) AS invoice_partner_display_name,
        STRING_AGG(DISTINCT
            CASE WHEN rp2.name IS NOT NULL AND rp2.name <> ''
                 THEN rp2.name || COALESCE(' (' || rc2.name || ')', '')
            END,
            ', ') AS invoice_additional_salespersons,
        STRING_AGG(DISTINCT rc2.name, ', ') AS invoice_additional_salespersons_companies,
        MAX(am.amount_total_signed - am.amount_residual_signed) AS invoice_paid_amount,
        COALESCE(MAX(pd.third_party_deduction), 0) AS third_party_deduction,
        COALESCE((MAX(am.amount_total_signed - am.amount_residual_signed) - COALESCE(MAX(pd.third_party_deduction), 0)) * 0.05, 0) AS tax_deduction,
        COALESCE(MAX(am.amount_total_signed - am.amount_residual_signed), 0) - COALESCE(MAX(pd.third_party_deduction), 0)
        - COALESCE((MAX(am.amount_total_signed - am.amount_residual_signed) - COALESCE(MAX(pd.third_party_deduction), 0)) * 0.05, 0) AS net_paid,
        CASE WHEN COALESCE(MAX(ppi.participants_count), 1) > 0 THEN
            (
                COALESCE(MAX(am.amount_total_signed - am.amount_residual_signed), 0)
                - COALESCE(MAX(pd.third_party_deduction), 0)
                - COALESCE((MAX(am.amount_total_signed - am.amount_residual_signed) - COALESCE(MAX(pd.third_party_deduction), 0)) * 0.05, 0)
            ) / COALESCE(MAX(ppi.participants_count), 1)
        ELSE 0 END AS net_paid_after_split,
        EXISTS (
            SELECT 1
            FROM sale_commission_achievement_approval scaa
            WHERE scaa.report_related_res_id = am.id
              AND scaa.report_related_res_model = 'account.move'
        ) AS is_approved,
        'account.move' AS related_res_model
    FROM invoices_rules rules
    JOIN account_move am ON am.company_id = rules.company_id
    JOIN account_move_line aml ON aml.move_id = am.id
    LEFT JOIN product_product pp ON aml.product_id = pp.id
    LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
    JOIN res_partner partner ON partner.id = am.partner_id
    JOIN invoice_participants ip ON ip.invoice_id = am.id
    LEFT JOIN participants_per_invoice ppi ON ppi.invoice_id = am.id
    LEFT JOIN invoice_participants ip2 ON ip2.invoice_id = am.id AND ip2.user_id <> ip.user_id
    LEFT JOIN res_users ru2 ON ru2.id = ip2.user_id
    LEFT JOIN res_partner rp2 ON rp2.id = ru2.partner_id
    LEFT JOIN res_company rc2 ON rc2.id = ru2.company_id
    LEFT JOIN payment_deductions_per_invoice pd ON pd.invoice_id = am.id

    WHERE am.move_type = 'out_invoice'
      AND am.state = 'posted'
      AND am.date BETWEEN rules.date_from AND rules.date_to
      AND (
          rules.product_id IS NULL OR rules.product_id = aml.product_id
      )
      AND (
          rules.product_categ_id IS NULL OR pt.categ_id = rules.product_categ_id
      )
      AND (
        (rules.team_rule AND am.team_id = rules.team_id)
        OR
        (NOT rules.team_rule AND ip.user_id = rules.user_id)
      )
    {'AND ip.user_id IN (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
    {'AND am.team_id IN (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
    GROUP BY am.id, rules.plan_id, ip.user_id
)
""", 'invoice_commission_lines'
