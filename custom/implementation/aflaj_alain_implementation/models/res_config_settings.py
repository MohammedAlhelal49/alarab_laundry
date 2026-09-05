# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models


class ResConfigSettingsInherited(models.TransientModel):
    _inherit = 'res.config.settings'

    chicken = fields.Many2one(
        'product.product', string="Chicken", related="company_id.chicken", readonly=False)

    dead_chicken = fields.Many2one(
        'product.product', string="Dead Chicken", related="company_id.dead_chicken", readonly=False)

    chicken1 = fields.Many2one(
        'product.product', string="Production brown chicken", related="company_id.chicken1", readonly=False)

    dead_chicken1 = fields.Many2one(
        'product.product', string="Dead Production brown chicken", related="company_id.dead_chicken1", readonly=False)

    chicken2 = fields.Many2one(
        'product.product', string="Production white chicken", related="company_id.chicken2", readonly=False)

    dead_chicken2 = fields.Many2one(
        'product.product', string="Dead Production white chicken", related="company_id.dead_chicken2", readonly=False)

    chicken3 = fields.Many2one(
        'product.product', string="Mother female chicken", related="company_id.chicken3", readonly=False)

    dead_chicken3 = fields.Many2one(
        'product.product', string="Dead Mother female chicken", related="company_id.dead_chicken3", readonly=False)

    chicken4 = fields.Many2one(
        'product.product', string="Mother female male rooster chicken", related="company_id.chicken4", readonly=False)

    dead_chicken4 = fields.Many2one(
        'product.product', string="Dead Mother female male rooster chicken", related="company_id.dead_chicken4", readonly=False)

    chicken_operation = fields.Many2one(
        'stock.picking.type', string="Chicken transfer operation type", related="company_id.chicken_operation",
        readonly=False)

    dead_chicken_operation = fields.Many2one(
        'stock.picking.type', string="Dead Chicken transfer operation type",
        related="company_id.dead_chicken_operation", readonly=False)

    production_operation = fields.Many2one(
        'stock.picking.type', string="Production egg transfer operation type",
        related="company_id.production_operation",
        readonly=False)

    broken_egg = fields.Many2one(
        'product.product', string="Broken Egg", related="company_id.broken_egg", readonly=False)

    rejected_egg = fields.Many2one(
        'product.product', string="Rejected Egg", related="company_id.rejected_egg", readonly=False)

    damaged_egg = fields.Many2one(
        'product.product', string="Damaged Egg", related="company_id.damaged_egg", readonly=False)

    mother_egg = fields.Many2one(
        'product.product', string="Mother Double Egg", related="company_id.mother_egg", readonly=False)

    chicken_egg = fields.Many2one(
        'product.product', string="Hatching Egg", related="company_id.chicken_egg", readonly=False)
