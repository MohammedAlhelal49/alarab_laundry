import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        """Capture each product line's Standard Price at the moment the
        customer invoice / refund is FIRST posted.

        Behaviour:
        - Writes to invoice product lines BEFORE delegating to super(), while
          the move is still 'draft' so the write is unrestricted.
        - Idempotent: only writes current_cost when it is still NULL. This means
          resetting an invoice to draft and re-posting it will NOT overwrite
          the original snapshot — the cost is truly frozen.
        - Covers customer invoices and credit notes from any source (manual,
          POS, e-commerce, sale order, etc.) since they all funnel through
          _post() before reaching state='posted'.
        """
        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund'):
                continue
            for line in move.invoice_line_ids:
                if line.display_type != 'product' or not line.product_id:
                    continue
                if line.current_cost:
                    # Snapshot already captured on a previous post — keep it.
                    continue
                product = line.product_id.with_company(move.company_id)
                line.current_cost = product.standard_price
                _logger.debug(
                    "dekad_invoice_product_profit: snapshot cost=%s for product %s on move %s",
                    product.standard_price, product.display_name, move.display_name,
                )
        return super()._post(soft=soft)
