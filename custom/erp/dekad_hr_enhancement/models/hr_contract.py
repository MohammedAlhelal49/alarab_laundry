from odoo import models, fields, api

class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_ae_total_allowances = fields.Monetary(
        string='Total Allowances',
        compute='_compute_l10n_ae_total_allowances',
        store=True,
        readonly=True,
        currency_field='currency_id',
    )

    additional_job_id = fields.Many2one(
        comodel_name='hr.job',
        string='Visa Job Position',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    additional_wage_type = fields.Selection(
        selection=[
            ('monthly', 'Fixed Wage'),
            ('hourly', 'Hourly Wage'),
        ],
        string='Wage Type',
    )

    additional_schedule_pay = fields.Selection(
        selection=[
            ('annually', 'Annually'),
            ('semi-annually', 'Semi-annually'),
            ('quarterly', 'Quarterly'),
            ('bi-monthly', 'Bi-monthly'),
            ('monthly', 'Monthly'),
            ('semi-monthly', 'Semi-monthly'),
            ('bi-weekly', 'Bi-weekly'),
            ('weekly', 'Weekly'),
            ('daily', 'Daily'),
        ],
        string='Schedule Pay',
    )

    actual_start_date = fields.Date(string="Actual Start Date")

    additional_wage = fields.Monetary(
        string='Wage',
        currency_field='currency_id',
    )
    additional_housing_allowance = fields.Monetary(
        string='Housing Allowance',
        currency_field='currency_id',
    )
    additional_transportation_allowance = fields.Monetary(
        string='Transportation Allowance',
        currency_field='currency_id',
    )
    additional_other_allowances = fields.Monetary(
        string='Other Allowances',
        currency_field='currency_id',
    )
    additional_total_allowances = fields.Monetary(
        string='Total Allowances',
        compute='_compute_additional_total_allowances',
        store=True,
        readonly=True,
        currency_field='currency_id',
    )

    @api.depends(
        'l10n_ae_housing_allowance',
        'l10n_ae_transportation_allowance',
        'l10n_ae_other_allowances',
        'wage',
    )
    def _compute_l10n_ae_total_allowances(self):
        for contract in self:
            contract.l10n_ae_total_allowances = (
                (contract.wage or 0.0)
                + (contract.l10n_ae_housing_allowance or 0.0)
                + (contract.l10n_ae_transportation_allowance or 0.0)
                + (contract.l10n_ae_other_allowances or 0.0)
            )


    @api.depends(
        'additional_housing_allowance',
        'additional_transportation_allowance',
        'additional_other_allowances',
        'additional_wage'
    )
    def _compute_additional_total_allowances(self):
        for contract in self:
            contract.additional_total_allowances = (
                (contract.additional_wage or 0.0)
                + (contract.additional_housing_allowance or 0.0)
                + (contract.additional_transportation_allowance or 0.0)
                + (contract.additional_other_allowances or 0.0)
            )