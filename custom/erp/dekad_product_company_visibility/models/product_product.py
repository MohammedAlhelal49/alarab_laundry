# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.osv import expression


class ProductProduct(models.Model):
    _inherit = 'product.product'

    company_visibility_id = fields.Many2one(
        comodel_name='res.company',
        string='Company allowed to see this product',
        related='product_tmpl_id.company_visibility_id',
        store=False,
        readonly=True,
    )

    company_visibility_ids = fields.Many2many(
        comodel_name='res.company',
        string='Companies allowed to see this product',
        related='product_tmpl_id.company_visibility_ids',
        store=False,
        readonly=True,
    )

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """ Same restriction as ProductTemplate.name_search - see that
        method's docstring for the full rationale. Overridden separately
        here because product.product has its own custom name_search
        implementation (multi-stage search by default_code/barcode/name)
        that does not simply delegate to product.template's version. """
        args = args or []
        visibility_domain = ['|',
            ('company_visibility_ids', '=', False),
            ('company_visibility_ids', 'in', self.env.companies.ids),
        ]
        args = expression.AND([args, visibility_domain])
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model
    def web_search_read(self, domain, *args, **kwargs):
        """ Same restriction as ProductTemplate.web_search_read - see that
        method's docstring for the full rationale. Overridden separately
        here since _inherits only delegates field access, not methods. """
        visibility_domain = ['|',
            ('company_visibility_ids', '=', False),
            ('company_visibility_ids', 'in', self.env.companies.ids),
        ]
        domain = expression.AND([domain, visibility_domain])
        return super().web_search_read(domain, *args, **kwargs)

    @api.model
    def web_read_group(self, domain, *args, **kwargs):
        """ Same restriction as ProductTemplate.web_read_group - see that
        method's docstring for the full rationale. Overridden separately
        here since _inherits only delegates field access, not methods. """
        visibility_domain = ['|',
            ('company_visibility_ids', '=', False),
            ('company_visibility_ids', 'in', self.env.companies.ids),
        ]
        domain = expression.AND([domain, visibility_domain])
        return super().web_read_group(domain, *args, **kwargs)
