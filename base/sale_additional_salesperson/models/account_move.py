from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    additional_invoice_user_id = fields.Many2many(
        comodel_name='res.users',
        relation='account_move_additional_user_rel',
        column1='move_id',
        column2='user_id',
        string='Additional Salespersons',
        copy=False,
        tracking=True,
        help='Additional salespersons copied from the related sale order.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to copy additional_user_id from sale.order
        to account.move.additional_invoice_user_id when invoice is created.
        """
        moves = super().create(vals_list)
        for move, vals in zip(moves, vals_list):
            if vals.get('invoice_origin'):
                origin = vals['invoice_origin']
                sale_order = self.env['sale.order'].search([('name', '=', origin)], limit=1)
                if sale_order and sale_order.additional_user_id:
                    move.additional_invoice_user_id = [(6, 0, sale_order.additional_user_id.ids)]
        return moves
