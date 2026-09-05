from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    can_move_locked_stage = fields.Boolean(
        string="Allow Moving Locked Stages",
        help="Allow this user to move opportunities from/to locked CRM stages."
    )