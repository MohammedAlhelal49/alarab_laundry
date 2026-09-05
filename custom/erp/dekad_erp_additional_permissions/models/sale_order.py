from odoo import models, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'


    # Restrict deletion to users in the 'sale_order_deletion' group
    def unlink(self):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_sale_order_deletion'):
            raise ValidationError(_("You do not have permission to delete Sale Orders."))
        return super().unlink()


    # Restrict cancellation to users in the 'sale_order_cancel' group
    def _action_cancel(self):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_sale_order_cancel'):
            raise ValidationError(_("You do not have permission to cancel Sale Orders."))
        return super()._action_cancel()

    # Restrict confirmation to users in the 'sale_order_confirm' group
    def action_confirm(self):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_sale_order_confirm'):
            raise ValidationError(_("You do not have permission to confirm Sale Orders."))
        return super().action_confirm()

