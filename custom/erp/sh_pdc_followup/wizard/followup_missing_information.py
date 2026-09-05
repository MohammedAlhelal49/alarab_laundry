from odoo import models, _


class PdcFollowupMissingInformation(models.TransientModel):
    _name = "pdc.followup.missing.information.wizard"
    _description = "PDC Followup missing information wizard"

    def view_partners_action(self):
        """Returns a list view containing all the partners with missing information."""
        view_id = self.env.ref('sh_pdc_followup.missing_information_view_tree').id
        return {
            'name': _('Missing information'),
            'res_model': 'res.partner',
            'view_mode': 'list',
            'views': [(view_id, 'list')],
            'domain': [('id', 'in', self.env.context.get('default_partner_ids', []))],
            'type': 'ir.actions.act_window',
        }
