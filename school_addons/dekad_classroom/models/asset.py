from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DeProductCategory(models.Model):
    _name = "de.product.category"
    _description = "Classroom products categories"
    name = fields.Char('name', required=True)


class DeProduct(models.Model):
    _name = "de.product"
    _description = "Classroom products"
    category_id = fields.Many2one('de.product.category', string="Category")
    name = fields.Char('name', required=True)
    image = fields.Image('Image')


class DeAsset(models.Model):
    _name = "de.asset"
    _description = "Classroom Assets"
    classroom_id = fields.Many2one('de.classroom', 'Classroom', ondelete="cascade")
    product_id = fields.Many2one('de.product', string="Product")
    qty = fields.Integer('Quantity', required=True)

    product_name = fields.Char(string="Name", related="product_id.name")
    product_image = fields.Image(string="Image", related="product_id.image")
    product_category = fields.Many2one('de.product.category', string="Category",
                                       related="product_id.category_id")
