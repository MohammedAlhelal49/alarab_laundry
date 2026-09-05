from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    auto_create_bom = fields.Boolean(string="Automated BoM Creation")
    prevent_invalid_mo_creation = fields.Boolean(string="Strict MO Validation")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_create_bom = fields.Boolean(
        related='company_id.auto_create_bom',
        readonly=False,
        string="Automated BoM Creation"
    )

    prevent_invalid_mo_creation = fields.Boolean(
        related='company_id.prevent_invalid_mo_creation',
        readonly=False,
        string="Strict MO Validation"
    )
