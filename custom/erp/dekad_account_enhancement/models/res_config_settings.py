from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    enable_credit_note_return = fields.Boolean(
        string="Enable Credit Note Return Delivery",
        config_parameter="dekad_account_enhancement.enable_credit_note_return",
    )

    group_discount_per_invoice_line = fields.Boolean(
        string='Discounts',
        implied_group='dekad_account_enhancement.group_discount_per_invoice_line',
    )

    invoice_discount_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Discount Product',
        related='company_id.invoice_discount_product_id',
        readonly=False,
    )

    dekad_default_customer_id = fields.Many2one(
        related='company_id.dekad_default_customer_id',
        string='Default Customer',
        readonly=False,
        help='This customer will be automatically set on new Customer '
             'Invoices / Credit Notes when the Customer field is left empty.',
    )

    refund_income_account_id = fields.Many2one(
        comodel_name='account.account',
        related='company_id.refund_income_account_id',
        string='Credit Note Income Account',
        readonly=False,
        domain=[('account_type', 'in', ['income', 'income_other'])],
        help='If set, customer credit notes will post income lines to this account '
             'instead of the original product income account.',
    )

