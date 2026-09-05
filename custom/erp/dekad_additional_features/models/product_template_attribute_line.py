from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    def _get_lock_reason(self):
        """Collect lock reason across all related templates."""
        for tmpl in self.mapped('product_tmpl_id'):
            is_locked, message = tmpl._get_lock_reason()
            if is_locked:
                return True, message
        return False, None

    def write(self, vals):
        is_locked, message = self._get_lock_reason()
        if is_locked:
            raise UserError(message)
        return super().write(vals)

    def unlink(self):
        is_locked, message = self._get_lock_reason()
        if is_locked:
            raise UserError(message)
        return super().unlink()