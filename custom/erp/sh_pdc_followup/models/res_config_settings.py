from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_pdc_followup = fields.Boolean(
        string="Enable PDC Follow-up"
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_pdc_followup = fields.Boolean(
        string="Enable PDC Follow-up",
        config_parameter="sh_pdc_followup.enable_pdc_followup"
    )

    def set_values(self):
        res = super().set_values()

        menu = self.env.ref('sh_pdc_followup.pdc_followup_menu', raise_if_not_found=False)
        if menu:
            menu.active = self.enable_pdc_followup

        return res
