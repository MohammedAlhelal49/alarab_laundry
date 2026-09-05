# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models


class ResCompanyInherited(models.Model):
    _inherit = 'res.company'

    chicken = fields.Many2one(
        'product.product', string="Chicken")

    dead_chicken = fields.Many2one(
        'product.product', string="Dead Chicken")

    chicken1 = fields.Many2one(
        'product.product', string="Production brown chicken")

    dead_chicken1 = fields.Many2one(
        'product.product', string="Dead Production brown chicken")

    chicken2 = fields.Many2one(
        'product.product', string="Production white chicken")

    dead_chicken2 = fields.Many2one(
        'product.product', string="Dead Production white chicken")

    chicken3 = fields.Many2one(
        'product.product', string="Mother female  chicken")

    dead_chicken3 = fields.Many2one(
        'product.product', string="Dead Mother female  chicken")

    chicken4 = fields.Many2one(
        'product.product', string="Mother female male rooster chicken")

    dead_chicken4 = fields.Many2one(
        'product.product', string="Dead Mother female male rooster chicken")


    chicken_operation = fields.Many2one(
        'stock.picking.type', string="Chicken transfer operation type")

    dead_chicken_operation = fields.Many2one(
        'stock.picking.type', string="Dead Chicken transfer operation type",
    )

    production_operation = fields.Many2one(
        'stock.picking.type', string="Production egg transfer operation type",
    )

    broken_egg = fields.Many2one(
        'product.product', string="Broken Egg")

    rejected_egg = fields.Many2one(
        'product.product', string="Rejected Egg")

    damaged_egg = fields.Many2one(
        'product.product', string="Damaged Egg")

    mother_egg = fields.Many2one(
        'product.product', string="Mother Double Egg")

    chicken_egg = fields.Many2one(
        'product.product', string="Hatching Egg")

