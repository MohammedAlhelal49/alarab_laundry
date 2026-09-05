# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models


class ResCompanyInherited(models.Model):
    _inherit = 'res.company'

    direct_purchase_receipt_invoice = fields.Boolean()

    direct_purchase_receipt_invoice_state = fields.Selection([
        ('draft', 'Draft bill'),
        ('posted', 'Posted bill'),

    ], string='Generated Bill state', default="draft")


    purchase_amount_total_words = fields.Boolean(
        string="Total amount of purchase order in letters",
        default=False,
    )

    direct_purchase_receipt_delivery_state = fields.Selection([
        ('draft', 'Draft delivery'),
        ('validated', 'Validated delivery'),

    ], string='Generated Delivery state', default="draft")

    purchase_discount_product_id = fields.Many2one(
        comodel_name='product.product',
        string="Purchase Discount Product",
        domain=[
            ('type', '=', 'service'),
            ('invoice_policy', '=', 'order'),
        ],
        help="Default product used as a negative line when applying a Global "
             "Discount or Fixed Amount discount on a Purchase Order. "
             "If not set, one will be created automatically the first time.",
        check_company=True,
    )


class ResConfigSettingsInherited(models.TransientModel):
    _inherit = 'res.config.settings'

    direct_purchase_receipt_invoice = fields.Boolean(related="company_id.direct_purchase_receipt_invoice", readonly=False)


    direct_purchase_receipt_invoice_state = fields.Selection([
        ('draft', 'Draft bill'),
        ('posted', 'Posted bill'),

    ], related="company_id.direct_purchase_receipt_invoice_state", readonly=False, string='Generated Bill state')

    direct_purchase_receipt_delivery_state = fields.Selection([
        ('draft', 'Draft delivery'),
        ('validated', 'Validated delivery'),

    ], string='Generated Delivery state', readonly=False, related="company_id.direct_purchase_receipt_delivery_state")


    # -----------------------------------------------------------------------
    # Feature flag
    # -----------------------------------------------------------------------
    group_purchase_discount_user = fields.Boolean(
        string="Purchase Discounts",
        # implied_group يفعّل/يعطّل الـ Group الظاهر في صفحة المستخدم.
        # المدير بعدها يختار يدوياً من يحصل على "Can Apply Discounts".
        implied_group='dekad_purchase_enhancement.group_purchase_discount_user',
        help="Allow selected users to apply discounts on Purchase Orders. "
             "After enabling, go to Settings → Users to assign the "
             "'Can Apply Discounts' permission per user.",
    )

    # -----------------------------------------------------------------------
    # Convenience field – lets the Settings page expose / configure the
    # discount product directly (same pattern as sale module).
    # -----------------------------------------------------------------------
    purchase_discount_product_id = fields.Many2one(
        comodel_name='product.product',
        related='company_id.purchase_discount_product_id',
        string="Purchase Discount Product",
        readonly=False,
    )
    purchase_amount_total_words = fields.Boolean(
        string="Total amount of purchase order in letters",
        related="company_id.purchase_amount_total_words",
        readonly=False,
    )