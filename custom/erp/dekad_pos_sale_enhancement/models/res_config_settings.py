from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_price_control_allowed_employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        related='pos_config_id.price_control_allowed_employee_ids',
        readonly=False,
        string='Employees Allowed to Override Price Control',
    )

    pos_use_strict_price_control_list = fields.Boolean(
        related='pos_config_id.use_strict_price_control_list',
        readonly=False,
        string='Restrict Price Control to Selected Employees Only',
    )