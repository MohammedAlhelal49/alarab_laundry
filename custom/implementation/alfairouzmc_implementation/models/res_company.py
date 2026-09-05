# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    restrict_negative_delivery = fields.Boolean(
        string='Restrict Negative Stock Output',
        default=False,
        help="If enabled, only the users listed below will be allowed to "
             "validate Delivery transfers that would bring a product's "
             "stock on hand below zero. All other users will be blocked."
    )

    negative_delivery_allowed_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='res_company_negative_delivery_allowed_users_rel',
        column1='company_id',
        column2='user_id',
        string='Users Allowed to Output Negative Stock',
        help="Only these users will be able to validate a Delivery that "
             "would make a product's stock on hand negative."
    )
