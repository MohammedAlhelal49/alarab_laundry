from odoo import fields, models, api


class StockPickingInherited(models.Model):
    _inherit = 'stock.picking'

    def handle_cost_amount_value(self):
        self.env['stock.move'].search([])._compute_unit_cost()
        self.env['stock.move.line'].search([])._compute_unit_cost()
        self.env['stock.move'].search([])._compute_cost_amount()
        self.env['stock.move.line'].search([])._compute_cost_amount()


class StockMoveInherited(models.Model):
    _inherit = 'stock.move'

    analytic_account_id = fields.Many2one('account.analytic.account', "Analytic account")

    unit_cost = fields.Float('Unit Cost', compute="_compute_unit_cost", store=True)
    cost_amount = fields.Float('Cost Amount', compute="_compute_cost_amount", store=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)

    @api.depends('product_id'  , 'product_id.standard_price')
    def _compute_unit_cost(self):
        for rec in self:
            rec.unit_cost = rec.product_id.standard_price

    @api.depends('unit_cost', 'quantity', 'product_uom_qty')
    def _compute_cost_amount(self):
        for rec in self:
            rec.cost_amount = rec.unit_cost * rec.quantity


class StockMoveLineInherited(models.Model):
    _inherit = 'stock.move.line'
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)
    analytic_account_id = fields.Many2one('account.analytic.account', "Analytic account",
                                          related="move_id.analytic_account_id")

    unit_cost = fields.Float('Unit Cost', compute="_compute_unit_cost", store=True)
    cost_amount = fields.Float('Cost Amount', compute="_compute_cost_amount", store=True)

    @api.depends('unit_cost', 'quantity')
    def _compute_cost_amount(self):
        for rec in self:
            rec.cost_amount = rec.unit_cost * rec.quantity

    @api.depends('product_id', 'product_id.standard_price')
    def _compute_unit_cost(self):
        for rec in self:
            rec.unit_cost = rec.product_id.standard_price
