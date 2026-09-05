# -*- coding: utf-8 -*-
from odoo import fields, models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    additional_user_id = fields.Many2many(
        comodel_name="res.users",
        relation="sale_order_additional_user_rel",
        column1="sale_order_id",
        column2="user_id",
        string="Additional Salespersons",
        domain=lambda self: [
            ('groups_id', '=', self.env.ref("sales_team.group_sale_salesman").id),
            ('share', '=', False),
        ],
        help="Extra salespeople responsible for this order. Manually assignable.",
        tracking=2,
    )
