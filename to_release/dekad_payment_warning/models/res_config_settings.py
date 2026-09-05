from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_payment_warning_message = fields.Boolean(
        string="Enable Payment Warning Message",
        config_parameter="dekad_payment_warning.enable_payment_warning_message"
    )

    payment_warning_message = fields.Char(
        string="Payment Warning Message",
        config_parameter="dekad_payment_warning.payment_warning_message"
    )

    payment_warning_excluded_groups = fields.Many2many(
        'res.groups',
        string="Excluded Groups",
        help="Users in these groups will NOT see the payment warning message."
    )

    def set_values(self):
        super().set_values()
        excluded_group_ids = ','.join(map(str, self.payment_warning_excluded_groups.ids))
        self.env['ir.config_parameter'].sudo().set_param(
            'dekad_payment_warning.excluded_groups_ids',
            excluded_group_ids
        )

    def get_values(self):
        res = super().get_values()
        group_ids_str = self.env['ir.config_parameter'].sudo().get_param(
            'dekad_payment_warning.excluded_groups_ids', ''
        )
        group_ids = [int(gid) for gid in group_ids_str.split(',') if gid]
        res.update({
            'payment_warning_excluded_groups': [(6, 0, group_ids)],
        })
        return res
