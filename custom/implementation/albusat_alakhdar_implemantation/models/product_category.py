# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    code = fields.Char(
        string='Code',
        required=True,
        help='Short code used as the prefix when auto-generating the '
             'sequential Code on product cards belonging to this category '
             '(e.g. "10" -> 100001, 100002, ...). Digits only.'
    )

    # @api.onchange('code')
    # def _onchange_code_digits_only(self):
    #     """ Silently strip any non-digit character the user may have
    #     typed, so only numbers ever stay in the field. """
    #     if self.code:
    #         digits_only = re.sub(r'\D', '', self.code)
    #         if digits_only != self.code:
    #             self.code = digits_only

    # @api.constrains('code')
    # def _check_code_digits_only(self):
    #     """ Hard rule enforced on save, regardless of where the data came
    #     from (form, import, API, ...). The onchange above only helps the
    #     UX when typing on the form; this is what actually guarantees the
    #     stored value is always digits only. """
    #     for category in self:
    #         if category.code and not category.code.isdigit():
    #             raise ValidationError(_(
    #                 'The Category Code must contain digits only (no '
    #                 'letters or symbols). You entered: "%s"'
    #             ) % category.code)
