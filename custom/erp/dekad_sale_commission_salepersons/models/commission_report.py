# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _


class SaleCommissionReport(models.Model):
    _inherit = "sale.commission.report"

    # NEW: Net Paid after split across all invoice participants
    net_paid_after_split = fields.Monetary(
        string="Net Paid (After Split)",
        readonly=True,
        currency_field='currency_id',
        help="Sum of net paid amounts after being split across invoice salespersons "
             "(primary + additional) within the target period."
    )

    @property
    def _table_query(self):
        """Rebuild the SQL view with an extra aggregated column from commission_lines:
           SUM(cl.net_paid_after_split) AS net_paid_after_split
        """
        users = self.env.context.get('commission_user_ids', [])
        if users:
            users = self.env['res.users'].browse(users).exists()
        teams = self.env.context.get('commission_team_ids', [])
        if teams:
            teams = self.env['crm.team'].browse(teams).exists()

        return f"""
WITH {self.env['sale.commission.achievement.report']._commission_lines_query(users=users, teams=teams)},
achievement AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY MAX(era.date_to) DESC, cl.user_id) AS id,
        era.id AS target_id,
        cl.plan_id AS plan_id,
        cl.user_id AS user_id,
        MIN(cl.team_id) AS team_id,
        cl.company_id AS company_id,
        GREATEST(SUM(cl.achieved), 0) AS achieved,
        CASE
            WHEN MAX(era.amount) > 0 THEN GREATEST(SUM(cl.achieved), 0) / MAX(era.amount)
            ELSE 0
        END AS achieved_rate,
        cl.currency_id AS currency_id,
        MAX(era.amount) AS amount,
        MAX(era.date_to) AS payment_date,
        MAX(scpf.id) AS forecast_id,
        MAX(scpf.amount) AS forecast,
        /* NEW aggregation from commission_lines */
        COALESCE(SUM(cl.net_paid_after_split), 0) AS net_paid_after_split
    FROM commission_lines cl
    JOIN sale_commission_plan_target era
        ON cl.plan_id = era.plan_id
        AND cl.date >= era.date_from
        AND cl.date <= era.date_to
    LEFT JOIN sale_commission_plan_target_forecast scpf
        ON (scpf.target_id = era.id AND cl.user_id = scpf.user_id)
    GROUP BY
        era.id,
        cl.plan_id,
        cl.user_id,
        cl.company_id,
        cl.currency_id
), target_com AS (
    SELECT
        amount AS before,
        target_rate AS rate_low,
        LEAD(amount) OVER (PARTITION BY plan_id ORDER BY target_rate) AS amount,
        LEAD(target_rate) OVER (PARTITION BY plan_id ORDER BY target_rate) AS rate_high,
        plan_id
    FROM sale_commission_plan_target_commission scpta
    JOIN sale_commission_plan scp ON scp.id = scpta.plan_id
    WHERE scp.type = 'target'
), achievement_target AS (
    SELECT
        a.id,
        a.target_id,
        a.plan_id,
        a.user_id,
        a.team_id,
        a.company_id,
        a.payment_date,
        a.currency_id,
        a.achieved,
        a.achieved_rate,
        a.amount AS target_amount,
        a.forecast,
        a.forecast_id,
        a.net_paid_after_split, -- NEW passthrough
        CASE
            WHEN tc.before IS NULL THEN a.achieved
            WHEN tc.rate_high IS NULL THEN tc.before
            ELSE tc.before + (tc.amount - tc.before) * (a.achieved_rate - tc.rate_low) / (tc.rate_high - tc.rate_low)
        END AS commission
    FROM achievement a
    LEFT JOIN target_com tc ON (
        tc.plan_id = a.plan_id AND
        tc.rate_low <= a.achieved_rate AND
        (tc.rate_high IS NULL OR tc.rate_high > a.achieved_rate)
    )
)
SELECT * FROM achievement_target
"""
