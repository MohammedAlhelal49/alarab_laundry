# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models, api, _


class ResCompanyInherited(models.Model):
    _inherit = 'res.company'

    enable_max_unvalidated_deliveries = fields.Boolean()
    sale_amount_total_words = fields.Boolean(
        string="Total amount of sale order in letters",
        default=False,
    )
    max_unvalidated_deliveries = fields.Integer(string='Max unvalidated deliveries count', default=0)

    direct_sale_delivery_invoice = fields.Boolean()

    direct_sale_delivery_invoice_state = fields.Selection([
        ('draft', 'Draft Invoice'),
        ('posted', 'Posted Invoice'),

    ], string='Generated Invoice state', default="draft")

    direct_sale_delivery_delivery_state = fields.Selection([
        ('draft', 'Draft delivery'),
        ('validated', 'Validated delivery'),

    ], string='Generated Delivery state', default="draft")



class ResConfigSettingsInherited(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_amount_total_words = fields.Boolean(
        string="Total amount of sale order in letters",
        related="company_id.sale_amount_total_words",
        readonly=False,
    )
    enable_max_unvalidated_deliveries = fields.Boolean(related="company_id.enable_max_unvalidated_deliveries",
                                                       readonly=False)

    max_unvalidated_deliveries = fields.Integer(related="company_id.max_unvalidated_deliveries",
                                                string='Max unvalidated deliveries count', readonly=False, )

    direct_sale_delivery_invoice = fields.Boolean(related="company_id.direct_sale_delivery_invoice", readonly=False)

    direct_sale_delivery_invoice_state = fields.Selection([
        ('draft', 'Draft Invoice'),
        ('posted', 'Posted Invoice'),

    ], string='Generated Invoice state', related="company_id.direct_sale_delivery_invoice_state", readonly=False)

    direct_sale_delivery_delivery_state = fields.Selection([
        ('draft', 'Draft delivery'),
        ('validated', 'Validated delivery'),

    ], string='Generated Delivery state', related="company_id.direct_sale_delivery_delivery_state", readonly=False)

