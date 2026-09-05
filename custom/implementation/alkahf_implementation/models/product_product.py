from odoo import models, fields
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_discount = fields.Boolean(string='Is Discount', default=False)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_discount = fields.Boolean(
        string='Is Discount',
        related='product_tmpl_id.is_discount',
        store=True,
        readonly=False
    )

    # @api.model
    # def create(self, vals):
    #     # Prevent creating a product with default_code = 'DISC' if one already exists
    #     if vals.get('default_code') == 'DISC':
    #         existing = self.search([('default_code', '=', 'DISC')], limit=1)
    #         if existing:
    #             raise UserError("A product with Internal Reference 'DISC' already exists.")
    #     return super().create(vals)
    #
    # def write(self, vals):
    #     # Prevent changing default_code of existing DISC product
    #     if 'default_code' in vals:
    #         for product in self:
    #             if product.default_code == 'DISC' and vals['default_code'] != 'DISC':
    #                 raise UserError("You can't change the Internal Reference of the discount product (DISC).")
    #
    #         # Prevent assigning 'DISC' to another product
    #         if vals['default_code'] == 'DISC':
    #             existing = self.search([('default_code', '=', 'DISC')], limit=1)
    #             # Check if the DISC is being reassigned to a different record
    #             for product in self:
    #                 if existing and existing.id != product.id:
    #                     raise UserError("A product with Internal Reference 'DISC' already exists.")
    #
    #     return super().write(vals)
    #
    # def unlink(self):
    #     # Prevent deleting the discount product
    #     for product in self:
    #         if product.default_code == 'DISC':
    #             raise UserError("You can't delete the discount product with Internal Reference 'DISC'.")
    #     return super().unlink()
    #

