# -*- coding: utf-8 -*-
from odoo import models, fields


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_restricted = fields.Boolean(
        string='Restricted Access',
        default=False,
        help="If enabled, only users listed in 'Allowed Users' will see this location.",
    )

    allowed_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='stock_location_allowed_users_rel',
        column1='location_id',
        column2='user_id',
        string='Allowed Users',
        help="Users who can see this location when 'Restricted Access' is enabled.",
    )
