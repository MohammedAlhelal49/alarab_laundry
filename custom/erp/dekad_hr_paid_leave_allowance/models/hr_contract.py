from odoo import fields, models, api


class HrContract(models.Model):
    _inherit = "hr.contract"

    ae_total_salary = fields.Monetary(
        string="AE Total Salary",
        compute="_compute_ae_total_salary",
        store=True,
        currency_field="currency_id",
    )

    @api.depends(
        "wage",
        "l10n_ae_housing_allowance",
        "l10n_ae_transportation_allowance",
        "l10n_ae_other_allowances",
    )
    def _compute_ae_total_salary(self):
        for contract in self:
            contract.ae_total_salary = (
                (contract.wage or 0.0)
                + (contract.l10n_ae_housing_allowance or 0.0)
                + (contract.l10n_ae_transportation_allowance or 0.0)
                + (contract.l10n_ae_other_allowances or 0.0)
            )
