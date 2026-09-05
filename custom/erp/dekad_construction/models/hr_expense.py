from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        help='The project this expense is linked to.'
    )

    task_id = fields.Many2one(
        'project.task',
        string='Project Task',
        help='Link this expense directly to a construction task tier.'
    )

    @api.model
    def default_get(self, fields_list):
        """Automatically grab the active project ID from the context
        when creating an expense from a project's subview."""
        res = super().default_get(fields_list)

        # Check if we are inside a project view
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        if active_model == 'project.project' and active_id:
            res['project_id'] = active_id
        elif self.env.context.get('default_project_id'):
            res['project_id'] = self.env.context.get('default_project_id')

        return res

    @api.constrains('task_id')
    def _check_task_level(self):
        for expense in self:
            if expense.task_id:
                parent = expense.task_id.parent_id
                if parent and parent.parent_id:
                    raise ValidationError(
                        _("You can only link a Task or a Level-1 Subtask.")
                    )
