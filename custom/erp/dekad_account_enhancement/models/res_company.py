from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    invoice_discount_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Discount Product (Invoices)',
        help='Product used to create discount lines on invoices and bills (Global Discount / Fixed Amount).',
    )

    dekad_default_customer_id = fields.Many2one(
        comodel_name='res.partner',
        string='Default Customer',
        help='This customer will be automatically set on new Customer '
             'Invoices / Credit Notes when the Customer field is left empty.',
    )

    refund_income_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Credit Note Income Account',
        check_company=True,
    )
