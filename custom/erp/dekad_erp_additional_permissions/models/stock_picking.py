from odoo import models, _
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Restrict validation to users with 'group_stock_picking_validate'
    def button_validate(self):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_stock_picking_validate'):
            raise ValidationError(_("You do not have permission to validate."))
        return super().button_validate()

    # Restrict cancellation to users with 'group_stock_picking_cancel'
    def action_cancel(self):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_stock_picking_cancel'):
            raise ValidationError(_("You do not have permission to cancel."))
        return super().action_cancel()

    # Restrict deletion to users with 'group_stock_picking_delete'
    def unlink(self):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_stock_picking_delete'):
            raise ValidationError(_("You do not have permission to delete."))
        return super().unlink()


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    # Restrict return operations to users with 'group_stock_picking_return'
    def _check_user_permission(self):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_stock_picking_return'):
            raise ValidationError(_("You do not have permission to return."))

    def action_create_returns(self):
        self._check_user_permission()
        return super().action_create_returns()

    def action_create_returns_all(self):
        self._check_user_permission()
        return super().action_create_returns_all()

    def action_create_exchanges(self):
        self._check_user_permission()
        return super().action_create_exchanges()

