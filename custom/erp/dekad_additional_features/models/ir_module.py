from odoo import models, fields, api


class IrModuleModuleInherited(models.Model):
    _inherit = 'ir.module.module'

    def uninstall_selected_modules(self):
            return self.button_immediate_uninstall() if self.state == 'installed' else print ('not installed')





