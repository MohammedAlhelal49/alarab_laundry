# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    restrict_negative_delivery = fields.Boolean(
        related='company_id.restrict_negative_delivery',
        readonly=False,
        string='Restrict Negative Stock Output',
    )

    negative_delivery_allowed_user_ids = fields.Many2many(
        related='company_id.negative_delivery_allowed_user_ids',
        readonly=False,
        string='Users Allowed to Output Negative Stock',
    )
