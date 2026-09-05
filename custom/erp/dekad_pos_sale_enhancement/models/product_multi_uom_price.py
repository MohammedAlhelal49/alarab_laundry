# -*- coding: utf-8 -*-
# © 2025 ehuerta _at_ ixer.mx
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).

from odoo import models, fields, api, _


class prod_tmpl_multi_uom(models.Model):
    _name = 'product.tmpl.multi.uom.price'
    _description = 'Product template multiple uom price'

    product_tmpl_id = fields.Many2one(
        'product.template',
        'Product Template',
        required=True,
        ondelete="cascade",
        readonly=True
    )
    category_id = fields.Many2one(related='product_tmpl_id.uom_id.category_id', readonly=True)
    uom_id = fields.Many2one('uom.uom',
                             string="Unit of Measure",
                             domain="[('category_id', '=', category_id)]",
                             required=True
                             )

    _sql_constraints = [
        ('product_tmpl_uom_uniq',
         'UNIQUE(product_tmpl_id, uom_id)',
         'Each Point of sale Unit of Measure must be unique per product template.')
    ]


class prod_multi_uom(models.Model):
    _name = 'product.multi.uom.price'
    _inherit = ['pos.load.mixin']
    _description = 'Product variant multiple uom price'

    product_id = fields.Many2one(
        'product.product',
        'Product variant',
        required=True,
        ondelete="cascade",
        readonly=True
    )
    category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    uom_id = fields.Many2one('uom.uom',
                             string="Unit of Measure",
                             domain="[('category_id', '=', category_id)]",
                             required=True
                             )

    @api.model
    def _load_pos_self_data_fields(self, config_id):
        return ['id', 'product_id', 'uom_id']

    _sql_constraints = [
        ('product_variant_uom_uniq',
         'UNIQUE(product_id, uom_id)',
         'Each Point of sale Unit of Measure must be unique per product variant.')
    ]
