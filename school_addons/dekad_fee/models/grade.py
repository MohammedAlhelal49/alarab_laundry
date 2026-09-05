from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DeGrade(models.Model):
    _inherit = "de.grade"
    fee_term_id = fields.Many2one('de.fee.term', string="Fee Terms", required=True)

    product_id = fields.Many2one('product.product', 'Register Fee ', required=True)

    fee = fields.Float('Register Fee amount', related="product_id.lst_price", readonly=True, store=True)
