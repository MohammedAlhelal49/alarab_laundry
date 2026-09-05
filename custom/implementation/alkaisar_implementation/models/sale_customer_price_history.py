from odoo import models, fields

class SaleCustomerPriceHistory(models.Model):
    _name = 'sale.customer.price.history'
    _description = 'Sale Customer Price History'
    _rec_name = 'product_id'

    product_id = fields.Many2one(
        'product.product',
        required=True,
        ondelete='cascade'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string="Customer",
        required=True,
        ondelete='cascade'
    )

    price_unit = fields.Float(
        string="Selling Price",
        required=True
    )

    date = fields.Datetime(
        string="Last Sale Date",
        required=True,
        default=fields.Datetime.now
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True
    )

    _sql_constraints = [
        (
            'unique_customer_product_company',
            'unique(partner_id, product_id, company_id)',
            'A price history already exists for this customer and product.'
        )
    ]
