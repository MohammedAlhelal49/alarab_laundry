# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    company_visibility_id = fields.Many2one(
        comodel_name='res.company',
        string='Company allowed to see this product',
        help=(
            'Legacy single-company field, kept visible for reference. '
            'The actual visibility/selection restriction is now driven '
            'by "Companies allowed to see this product" '
            '(company_visibility_ids) below - this field is only used '
            'to seed that one automatically (see create()/onchange), it '
            'no longer drives any access logic on its own.'
        ),
    )

    company_visibility_ids = fields.Many2many(
        comodel_name='res.company',
        relation='product_template_company_visibility_rel',
        column1='product_tmpl_id',
        column2='company_id',
        string='Companies allowed to see this product',
        help=(
            'If left empty, the product can be selected by users of any '
            'company (default Odoo behavior). If one or more companies '
            'are set, the product will only be found/selected by users '
            'currently working under one of those companies. '
            'Note: this field does NOT change the product\'s main '
            '"Company" field (company_id), so it has no effect on existing '
            'accounting entries or stock moves. This is the field that '
            'actually drives visibility - see company_visibility_id '
            '(above) for the legacy single-company field it is seeded '
            'from.'
        ),
    )

    @api.onchange('company_visibility_id')
    def _onchange_company_visibility_id_sync_ids(self):
        """ Keep company_visibility_ids in sync with the legacy
        company_visibility_id field when the user changes it interactively
        on the form: the selected company is ADDED to
        company_visibility_ids (union, not replace) so manually-added
        extra companies on the M2M are never silently removed by this
        sync. """
        for product in self:
            if product.company_visibility_id:
                product.company_visibility_ids = [(4, product.company_visibility_id.id)]

    @api.model_create_multi
    def create(self, vals_list):
        """Automatically fill company_visibility_id with the active company.

        Also initialize company_visibility_ids from company_visibility_id.
        Additionally, companies 3 and 4 are mutually visible:
            - Company 3 -> [3, 4]
            - Company 4 -> [4, 3]
        """
        LINKED_COMPANIES = {
            3: 4,
            4: 3,
        }

        for vals in vals_list:
            # Auto-fill company_visibility_id if needed
            if not vals.get('company_visibility_id') and not vals.get('company_id'):
                vals['company_visibility_id'] = self.env.company.id

            # Auto-fill company_visibility_ids if not explicitly provided
            if not vals.get('company_visibility_ids') and vals.get('company_visibility_id'):
                company_ids = [vals['company_visibility_id']]

                linked_company = LINKED_COMPANIES.get(vals['company_visibility_id'])
                if linked_company:
                    company_ids.append(linked_company)

                vals['company_visibility_ids'] = [(6, 0, list(set(company_ids)))]

        return super().create(vals_list)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """ Restrict autocomplete/dropdown results (RPC entry point called
        explicitly by the client - NOT part of Odoo's internal read-access
        check pipeline) to products that are either shared
        (company_visibility_ids empty) or visible to the user's active
        company. Confirmed via testing to cover the Sale Order Line
        product picker (which fires a name_search call once when the
        dropdown is opened, then filters locally as the user types). """
        args = args or []
        visibility_domain = ['|',
                             ('company_visibility_ids', '=', False),
                             ('company_visibility_ids', 'in', self.env.companies.ids),
                             ]
        args = expression.AND([args, visibility_domain])
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model
    def web_search_read(self, domain, *args, **kwargs):
        """ Restrict the results of the "Search More..." full list dialog
        and standard List/Kanban view data fetching (both use
        web_search_read, NOT name_search) to the same visibility rule.

        Like name_search, web_search_read is a top-level RPC entry point
        called explicitly by the web client - it is NOT part of the
        internal check_access('read') pipeline that _search()/ir.rule
        participate in. Overriding it here is safe: it never affects
        reading a product that is already linked to an existing document
        belonging to a different company (unlike an ir.rule or a
        _search() override, both of which were tested and confirmed to
        break access to historical Sale/Purchase Orders and Stock
        Pickings referencing such products).

        *args/**kwargs used instead of an explicit signature to stay
        resilient to any web_search_read signature changes across Odoo
        versions (e.g. 18 vs 19). """
        visibility_domain = ['|',
                             ('company_visibility_ids', '=', False),
                             ('company_visibility_ids', 'in', self.env.companies.ids),
                             ]
        domain = expression.AND([domain, visibility_domain])
        return super().web_search_read(domain, *args, **kwargs)

    @api.model
    def web_read_group(self, domain, *args, **kwargs):
        """ Restrict Kanban/List "Group By" bucket generation (group
        headers + counts + records within each group) to the same
        visibility rule.

        Confirmed via Network tab inspection: grouping a Kanban/List view
        by any field uses `web_read_group`, a SEPARATE RPC entry point
        from `web_search_read` - grouping by our own company_visibility_ids
        field was still showing a group bucket for a company other than
        the active one (with its products), because this method was not
        yet covered.

        Same safety profile as name_search/web_search_read: a top-level
        RPC entry point called explicitly by the client for building
        group buckets, not part of the internal check_access('read')
        pipeline - never affects reading a product already linked to an
        existing document. *args/**kwargs used for the same
        version-resilience reason as web_search_read. """
        visibility_domain = ['|',
                             ('company_visibility_ids', '=', False),
                             ('company_visibility_ids', 'in', self.env.companies.ids),
                             ]
        domain = expression.AND([domain, visibility_domain])
        return super().web_read_group(domain, *args, **kwargs)

    def action_seed_company_visibility_ids(self):
        """ Manually re-runnable version of the seeding step that
        normally happens once in post_init_hook (which only fires on
        module Install, never on Upgrade - see the module's development
        history for why this matters). Bound to a Server Action in
        views/product_template_views.xml, appearing in the "⚙ Actions"
        menu on the Products list/form, so it can be triggered on demand
        (e.g. right after an Upgrade) without needing shell access.

        Ignores the current recordset/selection on purpose and always
        scans ALL products - same idempotent behavior as the hook (only
        touches products where company_visibility_ids is still empty,
        never overwrites an already-populated value).
        """
        Product = self.env['product.template'].with_context(active_test=False)
        to_seed = Product.search([
            ('company_visibility_id', '!=', False),
            ('company_visibility_ids', '=', False),
        ])
        for product in to_seed:
            product.company_visibility_ids = [(6, 0, [product.company_visibility_id.id])]

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Company Visibility Sync'),
                'message': _('%s product(s) updated from the legacy field.', len(to_seed)),
                'type': 'success',
                'sticky': False,
            },
        }
