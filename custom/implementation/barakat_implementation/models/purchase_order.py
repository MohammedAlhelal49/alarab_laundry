from odoo import api, fields, models, _
from pytz import timezone
from datetime import datetime


class PurchaseOrderInherited(models.Model):
    _inherit = "purchase.order"

    @api.model
    def default_get(self, fields_list):
        res = super(PurchaseOrderInherited, self).default_get(fields_list)

        # Only set if partner_id is not already provided (e.g., from a duplicate or link)
        if 'partner_id' in fields_list and not res.get('partner_id'):
            param = self.env['ir.config_parameter'].sudo().get_param(
                'purchase.vendor_id'
            )
            if param:
                res['partner_id'] = int(param)

        return res

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)

        # Get all purchase managers
        purchase_admins = self.env.ref('purchase.group_purchase_manager').users

        # Create activity for each manager
        activity_type = self.env.ref('mail.mail_activity_data_todo')  # standard "To Do" type
        if not self.env.user.has_group('purchase.group_purchase_manager'):
            for order in orders:
                for user in purchase_admins:
                    self.env['mail.activity'].create({
                        'res_model_id': self.env['ir.model']._get_id('purchase.order'),
                        'res_id': order.id,
                        'activity_type_id': activity_type.id,
                        'user_id': user.id,
                        'summary': 'Purchase Order Awaiting Confirmation',
                        'note': f'Please review and confirm Purchase Order <b>{order.name}</b>.',
                        'date_deadline': fields.Date.today(),
                    })

        return orders

    def button_confirm(self):
        # If coming from wizard → skip wizard logic
        if self.env.context.get('skip_vendor_wizard'):
            return super().button_confirm()

        param = self.env['ir.config_parameter'].sudo().get_param('purchase.vendor_id')

        if param and self.partner_id.id == int(param):
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'confirm.purchase.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_purchase_id': self.id,
                }
            }
        else:
            return super().button_confirm()

