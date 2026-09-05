from odoo import models, api, _
from odoo.exceptions import ValidationError, AccessError

# Fields that require the "Contact Update" permission to change.
RESTRICTED_FIELDS = ('name', 'email', 'phone', 'mobile')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group(
                'dekad_erp_additional_permissions.group_contact_create'):
            raise ValidationError(
                _("You do not have permission to create contacts.")
            )

        return super().create(vals_list)

    def unlink(self):
        if not self.env.user.has_group(
                'dekad_erp_additional_permissions.group_contact_delete'):
            raise ValidationError(
                _("You do not have permission to delete contacts.")
            )

        return super().unlink()

    def write(self, vals):
        if any(field in vals for field in RESTRICTED_FIELDS) and \
                not self.env.user.has_group(
                    'dekad_erp_additional_permissions.group_contact_update'):
            raise AccessError(_(
                "You don't have the 'Contact Update' permission, so you "
                "are not allowed to change the Name, Email, Phone or "
                "Mobile of a Contact. Contact your administrator if you "
                "need this permission."
            ))
        return super().write(vals)


