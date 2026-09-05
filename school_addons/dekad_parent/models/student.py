from odoo import models, fields, api


class DeStudent(models.Model):
    _inherit = 'de.student'

    parent_ids = fields.Many2many('de.parent', string='Parents', copy=False)
    parent_count = fields.Integer(compute="_compute_parent_count", readonly=True, store=True)

    def _compute_parent_count(self):
        for rec in self:
            rec.parent_count = len(rec.parent_ids)

    def write(self, vals):
        res = super(DeStudent, self).write(vals)
        if vals.get('parent_ids', False):
            user_ids = []
            if self.parent_ids:
                for parent in self.parent_ids:
                    if parent.user_id:
                        user_ids = [parent.user_id.id for parent in parent.student_ids
                                    if parent.user_id]
                        parent.user_id.child_ids = [(6, 0, user_ids)]
            else:
                user_ids = self.env['res.users'].search([
                    ('child_ids', 'in', self.user_id.id)])
                for user_id in user_ids:
                    child_ids = user_id.child_ids.ids
                    child_ids.remove(self.user_id.id)
                    user_id.child_ids = [(6, 0, child_ids)]
        if vals.get('user_id', False):
            for parent_id in self.parent_ids:
                if parent_id.user_id:
                    child_ids = parent_id.user_id.child_ids.ids
                    child_ids.append(vals['user_id'])
                    parent_id.user_id.child_ids = [(6, 0, child_ids)]
        self.clear_caches()
        return res
