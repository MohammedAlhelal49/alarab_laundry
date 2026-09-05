from odoo import models, fields


class DeParentCreateUserWizard(models.TransientModel):
    _name = "de.parent.create.user.wizard"
    _description = "Create User for selected parent(s)"

    def _get_parents(self):
        if self.env.context and self.env.context.get('active_ids'):
            return self.env.context.get('active_ids')
        return []

    parent_ids = fields.Many2many(
        'de.parent', default=_get_parents, string='parents')

    def create_user(self):
        active_ids = self.env.context.get('active_ids', []) or []
        records = self.env['de.parent'].browse(active_ids)
        records.create_user()
