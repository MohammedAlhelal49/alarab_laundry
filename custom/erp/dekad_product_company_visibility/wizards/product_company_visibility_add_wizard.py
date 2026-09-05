# -*- coding: utf-8 -*-
from odoo import _, fields, models


class ProductCompanyVisibilityAddWizard(models.TransientModel):
    _name = 'product.company.visibility.add.wizard'
    _description = 'Add Companies to Product Visibility'

    product_tmpl_ids = fields.Many2many(
        comodel_name='product.template',
        string='Products',
        help='The products selected in the list view when this wizard was opened.',
    )
    company_ids = fields.Many2many(
        comodel_name='res.company',
        string='Companies to add',
        required=True,
        help=(
            'These companies will be ADDED to "Companies allowed to see '
            'this product" (company_visibility_ids) on every selected '
            'product, on top of whatever is already set there (e.g. by '
            'the "Sync Company Visibility" action or set manually) - '
            'existing values are never removed.'
        ),
    )

    def action_apply(self):
        self.ensure_one()
        if not self.product_tmpl_ids:
            return
        # (4, id) = add-to-relation without removing existing links,
        # applied for every company selected, on every selected product.
        add_commands = [(4, company.id) for company in self.company_ids]
        self.product_tmpl_ids.write({'company_visibility_ids': add_commands})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Company Visibility Updated'),
                'message': _(
                    '%(companies)s added to %(count)s product(s).',
                    companies=', '.join(self.company_ids.mapped('name')),
                    count=len(self.product_tmpl_ids),
                ),
                'type': 'success',
                'sticky': False,
            },
        }
