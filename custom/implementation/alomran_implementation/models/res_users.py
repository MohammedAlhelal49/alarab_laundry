from odoo import models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    def action_open_transfer_company_wizard(self):
        self.ensure_one()

        return {
            'name': _('Transfer Leads & Contacts'),
            'type': 'ir.actions.act_window',
            'res_model': 'transfer.company.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_user_id': self.id,
                'default_target_company_id': self.company_id.id,
            }
        }