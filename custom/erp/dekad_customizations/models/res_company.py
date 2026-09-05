# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    header_image = fields.Binary(
        string="Report Header Image",
        attachment=True,
        help="If set, this image replaces the standard header in PDF reports.",
    )

    footer_image = fields.Binary(
        string="Report Footer Image",
        attachment=True,
        help="If set, this image replaces the standard footer in PDF reports.",
    )