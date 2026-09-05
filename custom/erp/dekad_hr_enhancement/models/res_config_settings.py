from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    document_expiry_days = fields.Char(
        string="Reminder Days Before Expiry",
        default="30,7,3",
        config_parameter="hr.document_expiry_days",
        help="Comma-separated reminder days. Example: 30,7,3"
    )

    document_expiry_template_id = fields.Many2one(
        'mail.template',
        string="Document Expiry Email Template",
        config_parameter='hr.document_expiry_template_id'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'document_expiry_template_id' in fields_list:
            # Only set default if no value is already saved
            existing = self.env['ir.config_parameter'].sudo().get_param(
                'hr.document_expiry_template_id'
            )
            if not existing:
                template = self.env.ref(
                    'dekad_hr_enhancement.mail_template_document_expiry',
                    raise_if_not_found=False
                )
                if template:
                    res['document_expiry_template_id'] = template.id
        return res

    @api.constrains("document_expiry_days")
    def _check_document_expiry_days(self):
        for rec in self:
            if not rec.document_expiry_days:
                continue

            values = [v.strip() for v in rec.document_expiry_days.split(",")]

            for value in values:
                if not value.isdigit():
                    raise ValidationError(
                        "Reminder Days Before Expiry must contain only comma-separated positive integers (e.g. 30,7,3)."
                    )