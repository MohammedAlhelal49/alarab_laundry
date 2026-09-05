import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero

_logger = logging.getLogger(__name__)

APPLY_PHYSICAL_INVENTORY_GROUP = (
    'dekad_stock_enhancement.group_apply_physical_inventory'
)



class StockQuant(models.Model):
    _inherit = 'stock.quant'

    inventory_cost = fields.Float(
        string='Cost',
        digits='Product Price',
        compute='_compute_inventory_cost',
        store=True,
        readonly=False,
        help="Cost (Standard Price) of the product. "
             "Pre-filled with the current cost; editing it and clicking "
             "Apply updates the product's Cost.",
    )

    inventory_total = fields.Monetary(
        string='Total',
        compute='_compute_inventory_total',
        currency_field='company_currency_id',
        help="On Hand Quantity x Cost.",
    )

    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
    )

    @api.depends('product_id', 'product_id.standard_price')
    def _compute_inventory_cost(self):
        # We DO depend on standard_price so the column reflects the
        # product's current cost even after it changes externally
        # (purchases, AVCO recalculation, manual edits on the product
        # form, etc.) — not just when the line is first created.
        #
        # The risk this previously avoided: while _update_cost() is
        # writing the new cost to standard_price (during Apply), this
        # compute would fire mid-transaction and overwrite the value
        # the user just typed before super()._apply_inventory() runs.
        # We guard against that with a context flag set only during
        # our own _update_cost() write — see _update_cost() below.
        if self.env.context.get('dekad_skip_cost_recompute'):
            return
        for quant in self:
            if quant.product_id:
                quant.inventory_cost = quant.product_id.with_company(
                    quant.company_id or self.env.company
                ).standard_price
            else:
                quant.inventory_cost = 0.0

    @api.depends('quantity', 'inventory_cost')
    def _compute_inventory_total(self):
        for quant in self:
            quant.inventory_total = quant.quantity * quant.inventory_cost

    @api.model
    def _get_inventory_fields_write(self):
        return super()._get_inventory_fields_write() + ['inventory_cost']

    def _update_cost(self):
        """Update standard_price for quants where inventory_cost is set.

        Uses product.write({'standard_price': ...}) which is the correct
        Odoo pattern — the write() override in stock_account automatically:
          - Calls _change_standard_price() → SVL + revaluation journal entry
            when quantity_svl > 0 (existing stock)
          - Skips _change_standard_price() when quantity_svl = 0 (new product)
        In both cases standard_price is saved correctly in the DB.
        """
        # Run everything under dekad_skip_cost_recompute=True so that
        # ANY recompute of inventory_cost triggered during this method
        # (on self or any other quant of the same product) is skipped —
        # this context must be active for the whole method, not just the
        # final write(), because Odoo's recompute engine inherits the
        # env/context of the transaction that triggered it.
        self = self.with_context(dekad_skip_cost_recompute=True)

        price_prec = self.env['decimal.precision'].precision_get('Product Price')

        cost_quants = self.filtered(
            lambda q: q.product_id and not float_is_zero(
                q.inventory_cost, precision_digits=price_prec
            )
        )

        if not cost_quants:
            return

        # ------------------------------------------------------------------
        # Conflict check: same product, different costs across locations
        # ------------------------------------------------------------------
        cost_by_product = {}
        for quant in cost_quants:
            pid = quant.product_id.id
            cost = round(quant.inventory_cost, price_prec)
            if pid in cost_by_product:
                if float_compare(
                    cost_by_product[pid], cost,
                    precision_digits=price_prec
                ) != 0:
                    raise UserError(_(
                        "Product '%s' appears in multiple inventory lines "
                        "with different costs (%(c1)s vs %(c2)s).\n"
                        "Please make sure all lines for the same product "
                        "have the same cost before applying.",
                        quant.product_id.display_name,
                        c1=cost_by_product[pid],
                        c2=cost,
                    ))
            else:
                cost_by_product[pid] = cost

        # ------------------------------------------------------------------
        # Update standard_price per product via write()
        # stock_account's write() override handles SVL + journal entry
        # ------------------------------------------------------------------
        updated_products = self.env['product.product']
        for quant in cost_quants:
            if quant.product_id in updated_products:
                continue

            company = quant.company_id or self.env.company
            product = quant.product_id.with_company(company)

            # Skip if cost hasn't changed (this is what makes pre-filling
            # the field with the current cost SAFE: if the user doesn't
            # touch it, this condition is True and nothing happens).
            if float_compare(
                product.standard_price, quant.inventory_cost,
                precision_digits=price_prec
            ) == 0:
                updated_products |= quant.product_id
                continue

            _logger.info(
                "dekad_stock_enhancement: product=%s standard_price=%s "
                "→ inventory_cost=%s quantity_svl=%s",
                product.display_name, product.standard_price,
                quant.inventory_cost, product.sudo().quantity_svl,
            )

            # write() on product.product is the correct pattern:
            # stock_account intercepts it and calls _change_standard_price()
            # automatically — which creates the revaluation SVL and the
            # accounting journal entry when quantity_svl > 0.
            #
            # dekad_skip_cost_recompute is set explicitly here (not just
            # relied upon via inheritance) to guarantee it survives the
            # sudo() call and is active when stock_account's write()
            # override (and any resulting recompute) executes.
            product.sudo().with_context(
                self.env.context, dekad_skip_cost_recompute=True
            ).write({'standard_price': quant.inventory_cost})

            updated_products |= quant.product_id


    def _check_apply_physical_inventory_access(self):
        """Server-side guard: even if a user reaches these methods directly
        (e.g. via RPC) bypassing the view, block them unless they belong to
        the dedicated Apply Physical Inventory group.
        """
        if not self.env.user.has_group(APPLY_PHYSICAL_INVENTORY_GROUP):
            raise AccessError(_(
                "You are not allowed to apply physical inventory adjustments. "
                "Please contact your administrator to get the 'Apply Physical "
                "Inventory' access right."
            ))


    def action_apply_inventory(self):

        self._check_apply_physical_inventory_access()

        products_tracked_without_lot = []

        for quant in self:
            rounding = quant.product_uom_id.rounding

            if (
                fields.Float.is_zero(
                    quant.inventory_diff_quantity,
                    precision_rounding=rounding,
                )
                and fields.Float.is_zero(
                    quant.inventory_quantity,
                    precision_rounding=rounding,
                )
                and fields.Float.is_zero(
                    quant.quantity,
                    precision_rounding=rounding,
                )
            ):
                continue

            if (
                quant.product_id.tracking in ['lot', 'serial']
                and not quant.lot_id
                and quant.inventory_quantity != quant.quantity
                and not quant.quantity
            ):
                products_tracked_without_lot.append(
                    quant.product_id.id
                )

        quants_outdated = self.filtered(
            lambda quant: quant.is_outdated
        )

        if quants_outdated or products_tracked_without_lot:
            # Odoo is about to show a blocking dialog.
            # Do not change standard_price yet.
            return super().action_apply_inventory()

        # No blocking dialog: update cost before creating the stock move.
        self._update_cost()

        return super().action_apply_inventory()

    def action_apply_all(self):
        self._check_apply_physical_inventory_access()
        return super().action_apply_all()

class StockInventoryAdjustmentName(models.TransientModel):
    """Extend Apply All wizard to handle cost-only changes."""
    _inherit = 'stock.inventory.adjustment.name'

    def action_apply(self):
        # Cost-only quants won't pass through action_apply_inventory()
        # because the wizard filters by inventory_quantity_set only.
        cost_only_quants = self.quant_ids.filtered(
            lambda q: not q.inventory_quantity_set
        )
        _logger.info(
            "dekad_stock_enhancement: action_apply cost_only=%s",
            cost_only_quants.ids,
        )
        if cost_only_quants:
            cost_only_quants._update_cost()

        return super().action_apply()
