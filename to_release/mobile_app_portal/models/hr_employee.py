from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    allowed_mobile_app_ids = fields.Many2many(
        'mobile.app.config',
        related='user_id.allowed_mobile_app_ids',
        readonly=False,
        string="Allowed Mobile Apps",
        help="Mobile applications this employee's linked Odoo user is allowed to access."
    )
