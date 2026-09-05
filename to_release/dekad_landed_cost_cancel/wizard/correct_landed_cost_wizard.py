from odoo import models, fields, api
from odoo.exceptions import UserError


class CorrectLandedCostWizard(models.TransientModel):
    """
    Wizard for correcting a validated Landed Cost value.

    Supported scenario: no_sale only
        - All stock still in inventory (remaining_qty == original_qty)
        - Creates a corrective LC with the diff value

    Flow:
        1. Opens with current amount pre-filled
        2. User enters the correct amount
        3. Diff is computed automatically
        4. User confirms → corrective LC created
    """
    _name = 'correct.landed.cost.wizard'
    _description = 'Correct Landed Cost Wizard'

    landed_cost_id = fields.Many2one(
        'stock.landed.cost',
        string='Landed Cost',
        required=True,
        readonly=True,
    )
    current_amount = fields.Monetary(
        string='Current Amount',
        readonly=True,
        currency_field='currency_id',
    )
    correct_amount = fields.Monetary(
        string='Correct Amount',
        required=True,
        currency_field='currency_id',
    )
    diff_amount = fields.Monetary(
        string='Difference',
        compute='_compute_diff',
        currency_field='currency_id',
    )
    split_method = fields.Selection([
        ('equal',                 'Equal'),
        ('by_quantity',           'By Quantity'),
        ('by_current_cost_price', 'By Current Cost'),
        ('by_weight',             'By Weight'),
        ('by_volume',             'By Volume'),
    ], string='Split Method', required=True, default='by_quantity')

    currency_id = fields.Many2one(
        'res.currency',
        related='landed_cost_id.currency_id',
        readonly=True,
    )

    @api.depends('current_amount', 'correct_amount')
    def _compute_diff(self):
        for rec in self:
            rec.diff_amount = rec.correct_amount - rec.current_amount

    def action_confirm(self):
        self.ensure_one()

        # Guard 1: correct_amount must be positive
        if self.correct_amount < 0:
            raise UserError(
                "Correct amount cannot be negative.\n"
                "A Landed Cost value must always be 0 or greater."
            )

        if self.correct_amount == 0:
            raise UserError(
                "Correct amount cannot be zero.\n"
                "Use 'Cancel Landed Cost' instead to fully remove it."
            )

        if self.diff_amount == 0:
            raise UserError(
                "The correct amount equals the current amount. "
                "No correction needed."
            )

        self.landed_cost_id._lcc_do_correct(
            correct_amount=self.correct_amount,
            split_method=self.split_method,
        )

        return {'type': 'ir.actions.act_window_close'}