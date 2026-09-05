from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_mobile_app_ids = fields.Many2many(
        'mobile.app.config',
        'mobile_app_user_rel',
        'user_id',
        'app_id',
        string="Allowed Mobile Apps",
        help="Mobile applications this user is explicitly allowed to access."
    )
