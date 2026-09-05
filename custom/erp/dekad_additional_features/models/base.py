from odoo import models, api, _
from odoo.exceptions import UserError


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def _check_multi_company_lock(self):
        # We only care about UI interactions, ignore Odoo's internal Superuser
        if self.env.su:
            return

        # self.env.companies returns the records of all companies selected in the switcher
        active_companies = self.env.companies

        lock_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'multi_company_lock.prevent_edit'
        )

        if len(active_companies) > 1 and lock_enabled:
            # Check if ANY of the selected companies have the restriction enabled
                if self._name in ['res.users.log', 'mail.message', 'mail.tracking.value', 'bus.bus']:
                    return

                raise UserError(_(
                    "Security Policy: Data modification is disabled when multiple companies are active. "
                    "Please select only one company to proceed."
                ))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_multi_company_lock()
        return super().create(vals_list)

    def write(self, vals):
        self._check_multi_company_lock()
        return super().write(vals)

