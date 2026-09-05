from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    invoice_line_index = fields.Integer(
        string="#",
        compute="_compute_invoice_line_index",
        store=False,
    )

    journal_line_index = fields.Integer(
        string="#",
        compute="_compute_journal_line_index",
        store=False,
    )

    @api.depends("sequence", "move_id")
    def _compute_invoice_line_index(self):
        for line in self:
            line.invoice_line_index = 0

            if not line.move_id:
                continue

            lines = line.move_id.invoice_line_ids.sorted(
                key=lambda l: (l.sequence, l.id or 0)
            )

            for index, candidate in enumerate(lines, start=1):
                if candidate == line:
                    line.invoice_line_index = index
                    break

    @api.depends("sequence", "move_id")
    def _compute_journal_line_index(self):
        for line in self:
            line.journal_line_index = 0

            if not line.move_id:
                continue

            lines = line.move_id.line_ids.sorted(
                key=lambda l: (l.sequence, l.id or 0)
            )

            for index, candidate in enumerate(lines, start=1):
                if candidate == line:
                    line.journal_line_index = index
                    break