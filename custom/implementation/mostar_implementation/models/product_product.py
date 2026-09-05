from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    voucher_image = fields.Image(
        string='Voucher Print Image',
        max_width=512,
        max_height=512,
        help="This image will be displayed alongside the product description in the PDF voucher."
    )
