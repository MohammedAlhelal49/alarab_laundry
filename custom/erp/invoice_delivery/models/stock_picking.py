from odoo import _, api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    source_invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Source Invoice',
        copy=False,
        index=True,
        ondelete='set null',
        help='Customer invoice that created this delivery order.',
    )

    source_invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_source_invoice_count',
    )

    @api.depends('source_invoice_id')
    def _compute_source_invoice_count(self):
        for picking in self:
            picking.source_invoice_count = (
                1 if picking.source_invoice_id else 0
            )

    def action_view_source_invoice(self):
        self.ensure_one()

        if not self.source_invoice_id:
            return False

        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'views': [
                (
                    self.env.ref('account.view_move_form').id,
                    'form',
                )
            ],
            'res_id': self.source_invoice_id.id,
            'target': 'current',
        }




class StockMove(models.Model):
    _inherit = 'stock.move'

    source_invoice_line_id = fields.Many2one(
        comodel_name='account.move.line',
        string='Source Invoice Line',
        copy=False,
        index=True,
        ondelete='set null',
        help='Invoice line that created this stock move.',
    )