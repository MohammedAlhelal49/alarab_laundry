from odoo import models, _
from odoo.exceptions import ValidationError

class AccountAccount(models.Model):
    _inherit = 'account.account'

    def unlink(self):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_account_account_delete'):
            raise ValidationError(_("You do not have permission to delete an account."))
        return super().unlink()


    def create(self , vals):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_account_account_create'):
            raise ValidationError(_("You do not have permission to create an account."))
        return super().create(vals)

