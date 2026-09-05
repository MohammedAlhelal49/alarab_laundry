# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    code = fields.Char(
        string='Code',
        copy=False,
        help='Auto-suggested the first time a real Category (one with '
             'its own Code) is selected. The first product in a '
             'category gets the Category Code itself; each new '
             'product after that takes the last product\'s code in '
             'that category and bumps its trailing number by 1.'
    )

    categ_id = fields.Many2one(required=True)

    origin = fields.Char(string='Origin')
    brand = fields.Char(string='Brand')

    minimum_price = fields.Float(string='Minimum Price')
    maximum_price = fields.Float(string='Maximum Price')

    @api.onchange('categ_id')
    def _onchange_categ_id_code(self):
        """ Suggest a default Code as soon as a REAL category (one that
        has its own Code configured) is picked.

        On a brand-new, unsaved product we always (re)compute the code
        whenever the category changes. This also covers the case where
        the category field is set through a multi-step selection
        (parent, then child), where an earlier intermediate step may
        already have triggered this onchange once for a DIFFERENT
        (wrong) category, which used to leave a stale/incorrect code
        behind since it was never recalculated afterward.

        On an EXISTING, already-saved product we only fill the code if
        it's empty - we never silently overwrite an already-established
        code just because the category was edited afterward. """
        if not (self.categ_id and self.categ_id.code):
            return
        if not self.id or not self.code:
            self.code = self._generate_product_code(self.categ_id)

    # @api.onchange('code')
    # def _onchange_code_digits_only(self):
    #     """ Silently strip any non-digit character the user may have
    #     typed manually, so only numbers ever stay in the field. """
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
    #     for product in self:
    #         if product.code and not product.code.isdigit():
    #             raise ValidationError(_(
    #                 'The Product Code must contain digits only (no '
    #                 'letters or symbols). You entered: "%s"'
    #             ) % product.code)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') and vals.get('categ_id'):
                category = self.env['product.category'].browse(
                    vals['categ_id'])
                if category.code:
                    vals['code'] = self._generate_product_code(category)
        return super().create(vals_list)

    @api.model
    def _increment_code(self, code):
        """ Bump the trailing number of `code` by 1.

        - If `code` ends with digits (e.g. "112m005", "0", "2", or
          "1.1.1.5"), only that trailing numeric part is incremented,
          keeping the same digit width via zero-padding (e.g. "0" ->
          "1", "005" -> "006").
        - If `code` ends with a non-digit character - a letter or any
          other symbol (e.g. "112m" or "ssm") - there's nothing to
          increment, so a new numeric segment is appended instead,
          starting at 1 (e.g. "112m" -> "112m1"). From then on the code
          ends with a digit again, so future increments just bump that
          number normally ("112m1" -> "112m2" -> ...).
        """
        match = re.search(r'(\d+)$', code)
        if match:
            digits = match.group(1)
            prefix = code[:-len(digits)]
            next_number = int(digits) + 1
            return prefix + str(next_number).zfill(len(digits))
        return code + '1'

    def _generate_product_code(self, category):
        """ Next code for a product in `category`:
        - If this is the FIRST product ever in this category, use the
          category's own Code as the starting point.
        - Otherwise, take the LAST product's code in this category (the
          most recently created one, regardless of who/what created it
          - manual entry, this module, or an Excel import) and bump it
          by 1 using `_increment_code`. The category's own Code is NOT
          used as a prefix/basis here anymore - only the last product's
          actual code matters. """
        last_product = self.search([
            ('categ_id', '=', category.id),
            ('code', '!=', False),
        ], order='id desc', limit=1)

        if last_product and last_product.code:
            return self._increment_code(last_product.code)

        return category.code