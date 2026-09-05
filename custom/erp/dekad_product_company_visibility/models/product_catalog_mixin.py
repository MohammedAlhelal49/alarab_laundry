# -*- coding: utf-8 -*-
from odoo import models
from odoo.osv import expression


class ProductCatalogMixin(models.AbstractModel):
    _inherit = 'product.catalog.mixin'

    def _get_product_catalog_domain(self):
        """ Extend the base catalog domain (documented by Odoo itself as
        the intended extension point for hiding products from the
        "Catalog" picker) with our company visibility rule.

        This single override transparently covers every model that
        inherits `product.catalog.mixin` and calls
        `super()._get_product_catalog_domain()` - confirmed to include (at
        least): sale.order, purchase.order, mrp.bom, mrp.production (raw
        and byproduct catalogs), repair.order, and account.move (invoice
        lines) - without needing a separate override per module.

        Same safety profile as name_search()/web_search_read(): this
        domain only shapes the action's `domain` field (i.e. what gets
        fetched into the catalog kanban view), evaluated once when the
        "Catalog" button is clicked - it plays no part in Odoo's internal
        check_access('read') pipeline, so it never affects reading a
        product already linked to an existing document.
        """
        domain = super()._get_product_catalog_domain()
        visibility_domain = ['|',
            ('company_visibility_ids', '=', False),
            ('company_visibility_ids', 'in', [self.company_id.id]),
        ]
        return expression.AND([domain, visibility_domain])
