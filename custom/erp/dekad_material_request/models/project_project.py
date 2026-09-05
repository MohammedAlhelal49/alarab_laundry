from odoo import api, fields, models, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    material_request_ids = fields.One2many(
        'gmr.request', 'project_id', string='Material Requests'
    )
    material_request_count = fields.Integer(
        compute='_compute_material_request_count',
        string='Material Request Count'
    )

    @api.depends('material_request_ids')
    def _compute_material_request_count(self):
        read_group = self.env['gmr.request']._read_group(
            [('project_id', 'in', self.ids)], ['project_id'], ['__count']
        )
        mapped_count = {project.id: count for project, count in read_group}
        for project in self:
            project.material_request_count = mapped_count.get(project.id, 0)

    def action_view_material_requests(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Material Requests'),
            'res_model': 'gmr.request',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
        if self.material_request_count == 1 and not self.env.context.get('from_embedded_action'):
            action.update({
                'view_mode': 'form',
                'res_id': self.material_request_ids.id,
            })
        return action