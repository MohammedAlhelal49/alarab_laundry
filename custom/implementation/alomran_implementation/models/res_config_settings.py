from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    duplicate_contact_policy = fields.Selection([
        ('warning', 'Warning Only'),
        ('block', 'Prevent Duplicates'),
    ], default='warning')



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_auto_transfer = fields.Boolean(string="Enable Opportunity Transfer after Inactivity")
    auto_transfer_duration_days = fields.Integer(string="Transfer Duration (Days)")
    duplicate_contact_policy = fields.Selection(
        related='company_id.duplicate_contact_policy',
        readonly=False
    )


    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param('alomran_implementation.enable_auto_transfer', self.enable_auto_transfer)
        self.env['ir.config_parameter'].sudo().set_param('alomran_implementation.auto_transfer_duration_days', self.auto_transfer_duration_days)

    def get_values(self):
        res = super().get_values()
        res.update({
            'enable_auto_transfer': self.env['ir.config_parameter'].sudo().get_param('alomran_implementation.enable_auto_transfer') == 'True',
            'auto_transfer_duration_days': int(self.env['ir.config_parameter'].sudo().get_param('alomran_implementation.auto_transfer_duration_days', default=10)),
        })
        return res
