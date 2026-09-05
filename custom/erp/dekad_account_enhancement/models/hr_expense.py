from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"
    _order = "sequence, id"

    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )

    line_index = fields.Integer(
        string="Line #",
        compute="_compute_line_index",
        store=False,
    )


    @api.depends("sheet_id", "sheet_id.expense_line_ids.sequence")
    def _compute_line_index(self):
        # Default value for every record
        for expense in self:
            expense.line_index = 0

        # Compute numbering per sheet
        for sheet in self.mapped("sheet_id"):
            lines = sheet.expense_line_ids.sorted(lambda l: (l.sequence, l.id or 0))
            for idx, expense in enumerate(lines, start=1):
                expense.line_index = idx