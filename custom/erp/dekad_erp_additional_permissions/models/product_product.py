from odoo import models, _
from odoo.exceptions import ValidationError

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def unlink(self):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_product_product_delete'):
            raise ValidationError(_("You do not have permission to delete an product."))
        return super().unlink()


    def create(self , vals):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_product_product_create'):
            raise ValidationError(_("You do not have permission to create an product."))
        return super().create(vals)



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def unlink(self):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_product_product_delete'):
            raise ValidationError(_("You do not have permission to delete an product."))
        return super().unlink()

    def create(self , vals):
        if not self.env.user.has_group('dekad_erp_additional_permissions.group_product_product_create'):
            raise ValidationError(_("You do not have permission to create an product."))
        return super().create(vals)

