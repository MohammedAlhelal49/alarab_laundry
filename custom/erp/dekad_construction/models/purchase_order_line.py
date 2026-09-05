from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # The project associated with the entire Purchase Order
    project_id = fields.Many2one(
        'project.project',
        string='Project'
    )

    @api.model
    def default_get(self, fields_list):
        res = super(PurchaseOrder, self).default_get(fields_list)

        # Only set if partner_id is not already provided (e.g., from a duplicate or link)
        if 'partner_id' in fields_list and not res.get('partner_id'):
            param = self.env['ir.config_parameter'].sudo().get_param(
                'purchase.vendor_id'
            )
            if param:
                res['partner_id'] = int(param)

        return res

    def button_confirm(self):
        default_vendor_param = self.env['ir.config_parameter'].sudo().get_param('purchase.vendor_id')

        if default_vendor_param:
            default_vendor_id = int(default_vendor_param)
            for order in self:
                if order.partner_id.id == default_vendor_id:
                    raise UserError(_(
                        "Validation Error: You are still using the Default Vendor (%s). "
                        "Please select a real supplier before confirming this order."
                    ) % order.partner_id.name)

        return super(PurchaseOrder, self).button_confirm()

    def _prepare_invoice(self):
        """Pass the project_id to the draft vendor bill header."""
        invoice_vals = super(PurchaseOrder, self)._prepare_invoice()
        if self.project_id:
            invoice_vals['project_id'] = self.project_id.id
        return invoice_vals

    def _prepare_picking(self):
        """Pass the project_id to the stock picking header."""
        res = super()._prepare_picking()
        if self.project_id:
            res['project_id'] = self.project_id.id
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    task_id = fields.Many2one(
        'project.task',
        string='Project Task',
        help='Task this purchase line is related to'
    )

    @api.constrains('task_id')
    def _check_task_level(self):
        for line in self:
            if line.task_id:
                parent = line.task_id.parent_id
                if parent and parent.parent_id:
                    raise ValidationError(
                        _("You can only link a Task or a Level-1 Subtask.")
                    )

    def _prepare_account_move_line(self, move=False):
        """Pass the task_id to the generated vendor bill line."""
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        if self.task_id:
            res['task_id'] = self.task_id.id
        return res

    def _prepare_stock_moves(self, picking):
        """Pass task_id to the stock.move lines."""
        res = super()._prepare_stock_moves(picking)
        for move_vals in res:
            if self.task_id:
                move_vals['task_id'] = self.task_id.id
            return res