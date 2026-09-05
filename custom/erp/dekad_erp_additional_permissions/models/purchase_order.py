from odoo import models, _
from odoo.exceptions import ValidationError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Restrict confirming purchase orders
    def button_confirm(self):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_purchase_order_confirm'):
            raise ValidationError(_("You do not have permission to confirm purchase orders."))
        return super().button_confirm()

    # Restrict cancelling purchase orders
    def button_cancel(self):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_purchase_order_cancel'):
            raise ValidationError(_("You do not have permission to cancel purchase orders."))
        return super().button_cancel()

    # Restrict deleting purchase orders
    def unlink(self):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_purchase_order_delete'):
            raise ValidationError(_("You do not have permission to delete purchase orders."))
        return super().unlink()
