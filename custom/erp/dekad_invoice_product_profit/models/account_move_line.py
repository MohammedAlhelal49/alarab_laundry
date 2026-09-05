from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    current_cost = fields.Float(
        string='Stored Cost',
        readonly=True,
        copy=False,
        help="Product Standard Price captured at the moment the invoice was posted."
    )
