from odoo import models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class StockRule(models.Model):
    _inherit = "stock.rule"

    def _run_manufacture(self, procurements):
        """
        Intercept MO creation.
        Allow SO confirmation but block invalid MOs.
        """

        valid_procurements = []

        for procurement, rule in procurements:
            company = procurement.company_id

            # If the feature is OFF, allow everything to pass to standard Odoo logic
            if not company.prevent_invalid_mo_creation:
                valid_procurements.append((procurement, rule))
                continue

            product = procurement.product_id
            boms = self.env["mrp.bom"]._bom_find(
                products=product,
                company_id=company.id,
                picking_type=rule.picking_type_id,
                bom_type="normal",
            )
            bom = boms.get(product)

            # ❌ No BoM
            if not bom:
                _logger.warning(
                    "MO skipped for %s: no BoM found",
                    product.display_name,
                )
                continue

            # ❌ Empty BoM
            if not bom.bom_line_ids:
                _logger.warning(
                    "MO skipped for %s: empty BoM",
                    product.display_name,
                )
                continue

            # ❌ Zero / negative quantities
            if any(line.product_qty <= 0 for line in bom.bom_line_ids):
                _logger.warning(
                    "MO skipped for %s: zero-quantity BoM components",
                    product.display_name,
                )
                continue

            # ✅ Valid → allow MO creation
            valid_procurements.append((procurement, rule))

        # Call original logic ONLY for valid procurements
        if valid_procurements:
            return super()._run_manufacture(valid_procurements)

        return True
