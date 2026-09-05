# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    is_cancel_reversal = fields.Boolean(
        string="Wizard Cancel Reversal",
        default=False,
        index=True,
        help="Set when this valuation record is created by the Cancel/Draft Wizard.",
    )

    @api.model
    def create(self, vals):
        ctx = self.env.context or {}

        def _mark(v):
            if ctx.get("mark_as_cancel_reversal") and "is_cancel_reversal" not in v:
                v["is_cancel_reversal"] = True
            return v

        if isinstance(vals, list):
            vals = [_mark(v.copy()) for v in vals]
        else:
            vals = _mark(vals.copy())

        return super().create(vals)

    def action_delete_related_cancel_journal(self):
        for rec in self:
            if not rec.account_move_id or not rec.is_cancel_reversal:
                print('No journals no delete')
            else:
                rec.account_move_id.button_draft() if rec.account_move_id.state in ('posted', 'cancel') else print(
                    'no Journals to make draft')
                rec.account_move_id.unlink()

    def action_delete_related_cancel_journal_all(self):
        for item in self.search([]):
            item.action_delete_related_cancel_journal()
