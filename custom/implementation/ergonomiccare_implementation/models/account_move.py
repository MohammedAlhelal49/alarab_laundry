from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    patient_id = fields.Many2one(
        'res.partner',
        string='Patient Name',
        domain="[('is_company', '=', False)]",
    )

    claim_number = fields.Char(
        string="Claim No.",
    )


    lpo_authorization_type = fields.Selection(
        selection=[
            ('lpo', 'LPO Number'),
            ('authorization', 'Authorization Number'),
        ],
        string='LPO / Authorization No.',
    )

    lpo_number = fields.Char(string="LPO Number")
    authorization_number = fields.Char(string="Authorization Number")