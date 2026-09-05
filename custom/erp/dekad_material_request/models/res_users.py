from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Used to filter approver_id domain in views
    is_gmr_approver = fields.Boolean(
        string='Is GMR Approver',
        compute='_compute_is_gmr_approver',
        search='_search_is_gmr_approver',
    )

    @api.depends('groups_id')
    def _compute_is_gmr_approver(self):
        approver_group = self.env.ref('dekad_material_request.group_gmr_approver', raise_if_not_found=False)
        admin_group = self.env.ref('dekad_material_request.group_gmr_admin', raise_if_not_found=False)
        for user in self:
            in_approver = approver_group in user.groups_id if approver_group else False
            in_admin = admin_group in user.groups_id if admin_group else False
            user.is_gmr_approver = in_approver or in_admin

    @api.model
    def _search_is_gmr_approver(self, operator, value):
        approver_group = self.env.ref('dekad_material_request.group_gmr_approver', raise_if_not_found=False)
        admin_group = self.env.ref('dekad_material_request.group_gmr_admin', raise_if_not_found=False)
        user_ids = set()
        if approver_group:
            user_ids.update(approver_group.users.ids)
        if admin_group:
            user_ids.update(admin_group.users.ids)
        user_ids = list(user_ids)
        if not user_ids:
            return [('id', '=', False)]
        if operator == '=' and value:
            return [('id', 'in', user_ids)]
        return [('id', 'not in', user_ids)]
