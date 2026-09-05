# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Overhead(models.Model):
    _name = 'job.cost.overhead'
    _description = 'Job Cost Sheet Overhead Cost'

    sheet_id = fields.Many2one(
        'job.cost.sheet',
        required=True,
        ondelete='cascade'
    )

    overhead_tag_id = fields.Many2one(
        'job.cost.overhead.tag',
        string='Overhead Tag',
        required=True
    )
    description = fields.Text(string="Description")

    duration_type = fields.Selection([
        ('day', 'Day'),
        ('month', 'Month'),
        ('year', 'Year'),
    ], string="Duration Type", default='year')

    duration = fields.Float(string="Duration", default=1.0)
    planned_qty = fields.Float(string='Planned Qty', default=1.0)

    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    price_per_duration = fields.Float(string='Cost Per Duration', default=0.0)

    cost_price_subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_cost_price_subtotal',
        store=True
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('duration', 'price_per_duration')
    def _compute_cost_price_subtotal(self):
        for rec in self:
            rec.cost_price_subtotal = rec.duration * rec.price_per_duration

    # -------------------------------------------------------------------------
    # BUSINESS LOGIC / AUTO-FILL
    # -------------------------------------------------------------------------
    @api.onchange('overhead_tag_id')
    def _onchange_overhead_tag_id(self):
        """Auto-fill values from the selected overhead tag configuration."""
        for rec in self:
            if rec.overhead_tag_id:
                rec.description = rec.overhead_tag_id.description
                rec.price_per_duration = rec.overhead_tag_id.price


class OverheadTag(models.Model):
    _name = 'job.cost.overhead.tag'
    _description = 'Job Cost Sheet Overhead Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True)
    description = fields.Text(string="Description")
    price = fields.Float(string='Price', default=0.0)
