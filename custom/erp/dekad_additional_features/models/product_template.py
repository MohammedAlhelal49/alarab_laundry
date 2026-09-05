# -*- coding: utf-8 -*-

from odoo import models, api, _, fields
from odoo.osv import expression
from odoo.exceptions import UserError
import itertools


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    related_pricelist_price = fields.Float()
    has_stock_moves = fields.Boolean(
        string='Has Stock or Accounting Moves',
        compute='_compute_has_stock_moves',
        store=False,
    )

    is_discount = fields.Boolean(
        string="Is Discount",
        default=False,
    )

    lock_message = fields.Text(
        string='Lock Message',
        compute='_compute_lock_message',
        store=False,
    )

    x_product_search = fields.Char(
        string="Product Search",
        search="_search_x_product_search",
        store=False,
    )

    @api.model
    def _search_x_product_search(self, operator, value):
        if not value:
            return []

        products = self.env["product.product"].search([
            ("x_product_search", "ilike", value),
        ])

        return [
            ("product_variant_ids", "in", products.ids),
        ]


    def _compute_has_stock_moves(self):
        for record in self:
            stock = record._has_done_stock_moves()
            accounting = record._has_done_accounting_moves()

            record.has_stock_moves = stock or accounting

    def _compute_lock_message(self):
        for record in self:
            lines = []
            if record._has_done_stock_moves():
                variants = record._get_variants_with_stock_moves()
                names = ', '.join(variants.mapped('display_name'))
                lines.append(_("📦 Stock Moves (completed): %s") % names)
            if record._has_done_accounting_moves():
                variants = record._get_variants_with_accounting_moves()
                names = ', '.join(variants.mapped('display_name'))
                lines.append(_("💰 Accounting Moves (posted): %s") % names)
            record.lock_message = '\n'.join(lines) if lines else False

    # -------------------------------------------------------------------------
    # Stock moves check — all companies
    # -------------------------------------------------------------------------
    def _has_done_stock_moves(self):
        """Return True if any variant has at least one done stock move (all branches)."""
        self.ensure_one()
        product_ids = self.product_variant_ids.ids
        if not product_ids:
            return False

        groups = self.env['stock.move.line'].sudo().read_group(
            domain=[
                ('product_id', 'in', product_ids),
                ('move_id.state', '=', 'done'),
            ],
            fields=['product_id'],
            groupby=['product_id'],
            lazy=False,
        )
        return bool(groups)

    def _get_variants_with_stock_moves(self):
        """Return product.product recordset that have done stock moves (all branches)."""
        self.ensure_one()
        product_ids = self.product_variant_ids.ids
        if not product_ids:
            return self.env['product.product']

        groups = self.env['stock.move.line'].sudo().read_group(
            domain=[
                ('product_id', 'in', product_ids),
                ('move_id.state', '=', 'done'),
            ],
            fields=['product_id'],
            groupby=['product_id'],
            lazy=False,
        )
        ids_with_moves = [g['product_id'][0] for g in groups]
        return self.env['product.product'].browse(ids_with_moves)

    # -------------------------------------------------------------------------
    # Accounting moves check — all companies
    # -------------------------------------------------------------------------
    def _has_done_accounting_moves(self):
        """Return True if any variant has at least one posted accounting move (all branches)."""
        self.ensure_one()
        product_ids = self.product_variant_ids.ids
        if not product_ids:
            return False

        groups = self.env['account.move.line'].sudo().read_group(
            domain=[
                ('product_id', 'in', product_ids),
                ('move_id.state', '=', 'posted'),
            ],
            fields=['product_id'],
            groupby=['product_id'],
            lazy=False,
        )
        return bool(groups)

    def _get_variants_with_accounting_moves(self):
        """Return product.product recordset that have posted accounting moves (all branches)."""
        self.ensure_one()
        product_ids = self.product_variant_ids.ids
        if not product_ids:
            return self.env['product.product']

        groups = self.env['account.move.line'].sudo().read_group(
            domain=[
                ('product_id', 'in', product_ids),
                ('move_id.state', '=', 'posted'),
            ],
            fields=['product_id'],
            groupby=['product_id'],
            lazy=False,
        )
        ids_with_moves = [g['product_id'][0] for g in groups]
        return self.env['product.product'].browse(ids_with_moves)

    # -------------------------------------------------------------------------
    # Lock logic — smart message based on what exists
    # -------------------------------------------------------------------------
    def _get_lock_reason(self):
        """Returns (is_locked, reason_message) based on what moves exist."""
        self.ensure_one()
        has_stock = self._has_done_stock_moves()
        has_accounting = self._has_done_accounting_moves()

        if not has_stock and not has_accounting:
            return False, None

        lines = []

        if has_stock:
            variants = self._get_variants_with_stock_moves()
            lines.append(_(
                "📦 Stock Moves (completed):\n• %s"
            ) % '\n• '.join(variants.mapped('display_name')))

        if has_accounting:
            variants = self._get_variants_with_accounting_moves()
            lines.append(_(
                "💰 Accounting Moves (posted):\n• %s"
            ) % '\n• '.join(variants.mapped('display_name')))

        if has_stock and has_accounting:
            reason_title = _("This product has both completed stock moves and posted accounting moves.")
        elif has_stock:
            reason_title = _("This product has completed stock moves.")
        else:
            reason_title = _("This product has posted accounting moves.")

        message = _(
            "⛔ Cannot edit Attributes & Variants for product «%s»\n\n"
            "%s\n\n"
            "%s\n\n"
            "Editing Attributes will cause Variants to be archived, "
            "breaking your inventory and accounting data.\n\n"
            "Suggested alternative: Archive this product and create a new one."
        ) % (
                      self.name,
                      reason_title,
                      '\n\n'.join(lines),
                  )

        return True, message

    def _check_variants_lock(self, vals):
        """Block any write that touches attribute_line_ids when locked."""
        if 'attribute_line_ids' not in vals:
            return

        for record in self:
            is_locked, message = record._get_lock_reason()
            if is_locked:
                raise UserError(message)

    def write(self, vals):
        self._check_variants_lock(vals)
        return super().write(vals)

    def _create_variant_ids(self):
        """
        Intercept Odoo's internal variant generation engine.
        Skip check if we are already inside this call (context guard).
        """
        if self.env.context.get('_variant_lock_checked'):
            return super()._create_variant_ids()

        for template in self:
            is_locked, message = template._get_lock_reason()
            if is_locked:
                raise UserError(message)

        return super().with_context(_variant_lock_checked=True)._create_variant_ids()

    # -------------------------------------------------------------------------
    # Backward compatibility
    # -------------------------------------------------------------------------
    def _has_done_moves(self):
        return self._has_done_stock_moves() or self._has_done_accounting_moves()

    def _get_variants_with_moves(self):
        stock = self._get_variants_with_stock_moves()
        accounting = self._get_variants_with_accounting_moves()
        return stock | accounting


    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'is_storable' in fields_list:
            res['is_storable'] = True
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['company_id'] = self.env.company.id
        return super().create(vals_list)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []

        if not name:
            return super().name_search(
                name=name,
                args=args,
                operator=operator,
                limit=limit,
            )

        words = name.split()
        domain = []

        for word in words:
            word_domain = [
                ('x_product_search', operator, word),
            ]

            domain = expression.AND([domain, word_domain])

        args = expression.AND([args, domain])

        return super().name_search(
            name='',
            args=args,
            operator=operator,
            limit=limit,
        )


    def generate_variations_pricelist_rules(self):

        Pricelist = self.env['product.pricelist']
        PricelistItem = self.env['product.pricelist.item']

        # Fetch the default pricelist (you can adjust this condition)
        default_pricelist = self.env['product.pricelist'].search([('name', '=', 'Default')], limit=1)

        if not default_pricelist:
            default_pricelist = Pricelist.create({
                'name': 'Default',
                'currency_id': self.env.user.company_id.currency_id.id,
                'company_id': self.env.user.company_id.id,
            })

        for template in self:
            product_variation_ids = template.product_variant_ids.ids

            # Delete pricelist items for variants that no longer exist in the template
            PricelistItem.search([
                ('pricelist_id', '=', default_pricelist.id),
                ('product_id.product_tmpl_id', '=', template.id),
                ('product_id', 'not in', product_variation_ids)
            ]).unlink()

            # Create rules for missing variants
            existing_items = PricelistItem.search([
                ('pricelist_id', '=', default_pricelist.id),
                ('product_id.product_tmpl_id', '=', template.id),
            ])

            for variant in template.product_variant_ids:
                if not existing_items.filtered(
                        lambda item: item.product_id.id == variant.id):
                    PricelistItem.create({
                        'pricelist_id': default_pricelist.id,
                        'product_id': variant.id,
                        'applied_on': '0_product_variant',
                        'compute_price': 'fixed',
                        'fixed_price': variant.related_pricelist_price,
                    })

            for variant in template.product_variant_ids:
                UpdatePricelistItem = PricelistItem.search([
                    ('pricelist_id', '=', default_pricelist.id),
                    ('product_id', '=', variant.id),
                    ('applied_on', '=', '0_product_variant'),
                    ('compute_price', '=', 'fixed'),

                ])
                UpdatePricelistItem.write({
                    'fixed_price': variant.related_pricelist_price
                })

    def action_create_all_missing_variants(self):
        """
        Creates all missing product variants for the selected product templates,
        bypassing the 'dynamic' attribute setting.
        """
        Product = self.env['product.product']
        created_total = 0
        skipped = 0

        for template in self:
            lines_without_no_variants = template.attribute_line_ids._without_no_variant_attributes()

            # Skip templates with no attribute lines instead of raising an error
            if not lines_without_no_variants:
                skipped += 1
                continue

            all_variants = template.product_variant_ids.with_context(active_test=False)
            existing_variants = {
                variant.product_template_attribute_value_ids: variant for variant in all_variants
            }

            # Get all possible combinations
            all_combinations_generator = itertools.product(*[
                ptal.product_template_value_ids._only_active() for ptal in lines_without_no_variants
            ])

            variants_to_create = []

            for combination in template._filter_combinations_impossible_by_config(
                    all_combinations_generator, ignore_no_variant=True,
            ):
                if combination not in existing_variants:
                    variants_to_create.append(template._prepare_variant_values(combination))

            if variants_to_create:
                Product.create(variants_to_create)
                created_total += len(variants_to_create)

        # Display summary message
        message = ""
        if created_total:
            message += _("%s variants created successfully. " % created_total)
        if skipped:
            message += _("%s products skipped (no attribute lines)." % skipped)
        if not message:
            message = _("All possible variants already exist for all selected products.")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Variant Creation Summary'),
                'message': message,
                'sticky': False,
            }
        }




class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    def _get_combination_name(self):
        """Include attribute names in the combination name (e.g., 'Size: S; Color: Red')."""
        show_product_variation_attribute_name = self.env.company.show_product_variation_attribute_name
        names = []
        for ptav in self:
            attr = ptav.attribute_id.name or ''
            val = ptav.product_attribute_value_id.name or ''
            value_name = val
            attribute_value_name = f"{attr}: {val}"
            names.append(attribute_value_name if show_product_variation_attribute_name else value_name)
        return '; '.join(names)


class ProductCategory(models.Model):
    _inherit = "product.category"

    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        if 'property_cost_method' in fields_list:
            res['property_cost_method'] = 'average'

        return res
