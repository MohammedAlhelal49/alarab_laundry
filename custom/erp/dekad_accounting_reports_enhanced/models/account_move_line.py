from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        compute='_compute_analytic_account_id',
        store=True,
    )

    @api.depends('analytic_distribution')
    def _compute_analytic_account_id(self):
        for line in self:
            line.analytic_account_id = False

            distribution = line.analytic_distribution or {}
            first_key = next(iter(distribution), False)

            if first_key:
                line.analytic_account_id = int(first_key.split(',')[0])