from odoo import fields, models, api, _


class ResUsers(models.Model):
    _inherit = "res.users"

    allowed_sales_user_ids = fields.Many2many(
        "res.users",
        "res_users_sale_access_rel",
        "user_id",
        "allowed_user_id",
        string="Allowed Sales Users",
    )

    show_sales_access_tab = fields.Boolean(
        compute="_compute_show_sales_access_tab"
    )

    @api.depends("groups_id")
    def _compute_show_sales_access_tab(self):
        group = self.env.ref(
            "dekad_sale_enhancement.group_sale_selected_users",
            raise_if_not_found=False,
        )

        for user in self:
            user.show_sales_access_tab = group in user.groups_id if group else False


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