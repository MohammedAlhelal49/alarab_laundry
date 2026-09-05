from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_image = fields.Binary(
        string="Image",
        compute="_compute_product_image",
        store=True,
    )
    link = fields.Char(string='Link')

    barcode = fields.Char(related='product_id.barcode', store=False, readonly=True)


    @api.depends('product_id.image_128')
    def _compute_product_image(self):
        for line in self:
            line.product_image = (
                line.product_id.image_128 or
                line.product_id.product_tmpl_id.image_128
            )

    def handle_old_order_line_images(self):
        for line in self.search([]):
            line.product_image = (
                line.product_id.image_128 or
                line.product_id.product_tmpl_id.image_128
            )