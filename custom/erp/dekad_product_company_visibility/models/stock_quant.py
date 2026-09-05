# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.osv import expression


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def web_search_read(self, domain, *args, **kwargs):
        """ stock.quant is a SEPARATE model from product.template/
        product.product - it has its own `product_id` field and its own
        web_search_read entry point, so the overrides on the product
        models never apply here. Discovered via Network tab: opening
        Inventory > Operations > Physical Inventory (Inventory
        Adjustment) issues `POST .../stock.quant/web_search_read`,
        listing quant rows (one per product/location) completely outside
        our product-level restriction - same pattern as hr.expense.

        `company_visibility_id` is not a field on stock.quant, but domain
        leaves support dot-notation traversal through relations, and the
        field already exists (as a related field) on product.product via
        `product_id`, so we can reference it directly as
        `product_id.company_visibility_id` without needing any new field
        or helper model. """
        visibility_domain = ['|',
            ('product_id.company_visibility_ids', '=', False),
            ('product_id.company_visibility_ids', 'in', self.env.companies.ids),
        ]
        domain = expression.AND([domain, visibility_domain])
        return super().web_search_read(domain, *args, **kwargs)

    @api.model
    def web_read_group(self, domain, *args, **kwargs):
        """ Same restriction as web_search_read above, for Group By
        bucket generation on stock.quant (e.g. grouping the Inventory
        Adjustment list by product or location). """
        visibility_domain = ['|',
            ('product_id.company_visibility_ids', '=', False),
            ('product_id.company_visibility_ids', 'in', self.env.companies.ids),
        ]
        domain = expression.AND([domain, visibility_domain])
        return super().web_read_group(domain, *args, **kwargs)
