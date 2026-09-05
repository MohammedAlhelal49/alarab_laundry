from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    task_id = fields.Many2one(
        'project.task',
        string='Project Task',
        help='Task this journal item is related to',
        readonly="move_id.state == 'posted'",
    )

    # Stored related field allows direct grouping and SQL performance on Journal Items
    project_id = fields.Many2one(
        'project.project',
        related='move_id.project_id',
        string='Project',
        store=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Catch HR Expense Sheet linking
            if vals.get('expense_id') and not vals.get('task_id'):
                expense = self.env['hr.expense'].browse(vals['expense_id'])
                if expense.exists() and expense.task_id:
                    vals['task_id'] = expense.task_id.id

            # Catch manual Vendor Bill autocomplete line generation
            if vals.get('purchase_line_id') and not vals.get('task_id'):
                po_line = self.env['purchase.order.line'].browse(vals['purchase_line_id'])
                if po_line.exists() and po_line.task_id:
                    vals['task_id'] = po_line.task_id.id

        return super().create(vals_list)

    @api.constrains('task_id')
    def _check_task_level(self):
        for line in self:
            if line.task_id:
                parent = line.task_id.parent_id
                if parent and parent.parent_id:
                    raise ValidationError(
                        _("You can only link a Task or a Level-1 Subtask.")
                    )

    @api.onchange('move_id')
    def _onchange_move_currency(self):
        for line in self:
            if line.move_id:
                line.currency_id = line.move_id.currency_id


class AccountMove(models.Model):
    _inherit = 'account.move'

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        readonly="state == 'posted'",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # HR Expense Sheet Linking
            sheet_id = vals.get('expense_sheet_id') or self.env.context.get('default_expense_sheet_id')
            if sheet_id and not vals.get('project_id'):
                sheet = self.env['hr.expense.sheet'].browse(sheet_id)
                if sheet.exists():
                    projects = sheet.expense_line_ids.mapped('project_id')
                    if projects:
                        vals['project_id'] = projects[0].id

        return super().create(vals_list)

    @api.onchange('purchase_vendor_bill_id', 'purchase_id')
    def _onchange_purchase_auto_populate_project(self):
        """Catch project_id if user manually selects a PO from an empty draft Vendor Bill."""
        po = self.purchase_vendor_bill_id or self.purchase_id
        if po and po.project_id:
            self.project_id = po.project_id.id

    @api.onchange('currency_id')
    def _onchange_currency_warn(self):
        if self.line_ids:
            return {
                'warning': {
                    'title': "Currency Changed",
                    'message': (
                        "Changing the journal entry currency updates existing lines. "
                        "Please review and re-enter foreign currency amounts."
                    )
                }
            }
