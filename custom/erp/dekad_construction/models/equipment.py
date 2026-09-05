# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class Equipment(models.Model):
    _name = 'equipment'
    _description = 'Equipment Line'

    sheet_id = fields.Many2one(
        'job.cost.sheet',
        required=True,
        ondelete='cascade',
    )

    type = fields.Selection([
        ('equipment', 'Equipment'),
        ('machinery', 'Machinery'),
        ('vehicle', 'Vehicle'),
    ], string="Type", default='equipment')

    equipment_ownership_type = fields.Selection([
        ('asset', 'Asset'),
        ('rental', 'Rental'),
    ], string="Equipment Type", required=True, default='asset')

    asset_id = fields.Many2one('account.asset', string="Asset")

    product_id = fields.Many2one(
        'product.product',
        string="Equipment/Service",
        domain=[('type', '=', 'service')]
    )

    expenses = fields.Float(string="Expenses")
    date = fields.Date(string="Purchase Date")
    description = fields.Text(string="Description")
    simplified_equipment_cost = fields.Float(string="Equipment Cost")

    duration_type = fields.Selection([
        ('day', 'Day'),
        ('month', 'Month'),
        ('year', 'Year'),
    ], string="Duration Type", default='year')
    duration = fields.Float(string="Duration", default=1.0)

    equipment_cost_per_year = fields.Float(compute="_compute_costs", store=True, string="Equipment Cost / Year")
    fuel_cost_per_year = fields.Float(string="Fuel Cost / Year", default=0.0)
    service_cost_per_year = fields.Float(string="Service Cost / Year", default=0.0)
    total_cost_per_year = fields.Float(compute="_compute_costs", store=True, string="Total Cost / Year")

    productivity_per_year = fields.Float(string="Productivity / Year")
    uom_id = fields.Many2one('uom.uom', string="UoM")
    excavation_rate = fields.Float(compute="_compute_excavation", store=True, string="Excavation Rate")
    cost_price_subtotal = fields.Float(compute="_compute_excavation", store=True, string="Total Cost")
    price_per_duration = fields.Float(compute="_compute_costs", store=True, string="Cost / Year")

    currency_id = fields.Many2one('res.currency', related='sheet_id.currency_id', readonly=True, store=True)

    @api.onchange('duration', 'duration_type')
    def _onchange_duration_warning(self):
        for rec in self:
            if rec.duration_type == 'day' and rec.duration > 365:
                return {
                    'warning': {
                        'title': _("Unusual Duration"),
                        'message': _("You entered more than 365 days. Consider using months or years.")
                    }
                }

    def _duration_to_years(self):
        self.ensure_one()
        if self.duration <= 0: return 1.0
        if self.duration_type == 'year':
            return self.duration
        elif self.duration_type == 'month':
            return self.duration / 12.0
        elif self.duration_type == 'day':
            return self.duration / 365.0
        return 1.0

    @api.depends('expenses', 'duration', 'duration_type', 'fuel_cost_per_year', 'service_cost_per_year',
                 'simplified_equipment_cost')
    def _compute_costs(self):
        for rec in self:
            years = rec._duration_to_years()
            rec.equipment_cost_per_year = rec.expenses / years if years > 0 else rec.expenses
            rec.total_cost_per_year = rec.equipment_cost_per_year + rec.fuel_cost_per_year + rec.service_cost_per_year
            rec.price_per_duration = rec.simplified_equipment_cost * rec.duration

    @api.depends('total_cost_per_year', 'productivity_per_year', 'sheet_id.quantity', 'simplified_equipment_cost',
                 'price_per_duration')
    def _compute_excavation(self):
        for rec in self:
            if rec.productivity_per_year > 0:
                rec.excavation_rate = rec.total_cost_per_year / rec.productivity_per_year
            else:
                rec.excavation_rate = 0.0
            qty = rec.sheet_id.quantity or 0.0
            rec.cost_price_subtotal = rec.excavation_rate * qty if rec.simplified_equipment_cost == 0 else rec.price_per_duration

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        for rec in self:
            if rec.asset_id:
                rec.description = rec.asset_id.name

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                rec.description = rec.product_id.display_name
                rec.simplified_equipment_cost = rec.product_id.standard_price  # Pulls product Cost price
                if rec.product_id.uom_id:
                    rec.uom_id = rec.product_id.uom_id.id