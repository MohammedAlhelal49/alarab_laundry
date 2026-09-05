from odoo import models, fields

class CrmStage(models.Model):
    _inherit = "crm.stage"

    lock_stage = fields.Boolean(
        string="Lock Stage",
        help="If enabled, users cannot move opportunities into this stage."
    )

