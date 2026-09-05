from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProjectTaskDependency(models.Model):
    _name = 'project.task.dependency'
    _description = 'Task Dependency'

    predecessor_task_id = fields.Many2one(
        'project.task',
        string="Predecessor Task",
        required=True,
        ondelete='cascade'
    )

    successor_task_id = fields.Many2one(
        'project.task',
        string="Successor Task",
        required=True,
        ondelete='cascade'
    )

    project_id = fields.Many2one(
        'project.project',
        related='successor_task_id.project_id',
        store=True,
        readonly=True
    )

    dependency_type = fields.Selection([
        ('fs', 'Finish to Start'),
        ('ff', 'Finish to Finish'),
        ('ss', 'Start to Start'),
    ], default='fs', required=True)

    lag_days = fields.Integer(
        string="Lag (Days)",
        default=0,
        help="Delay after predecessor (>= 0)"
    )

    @api.constrains('predecessor_task_id', 'successor_task_id')
    def _check_no_cycles(self):
        if self.predecessor_task_id == self.successor_task_id:
            raise ValidationError(_("A task cannot depend on itself."))

    @api.onchange('lag_days')
    def _onchange_lag_days(self):
        if self.lag_days < 0:
            self.lag_days = 0
            return {
                'warning': {
                    'title': _('Invalid Lag'),
                    'message': _('Lag days cannot be negative.')
                }
            }

    @api.constrains('lag_days')
    def _check_lag_days_positive(self):
        for rec in self:
            if rec.lag_days < 0:
                raise ValidationError(
                    _("Lag days must be zero or a positive number.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Trigger recalculation for the successor tasks when a dependency is created
        for rec in records:
            if rec.successor_task_id:
                rec.successor_task_id._recalculate_schedule()
        return records

    def write(self, vals):
        res = super().write(vals)
        # If dependency rules change, recalculate the schedule
        trigger_fields = ['dependency_type', 'lag_days', 'predecessor_task_id', 'successor_task_id']
        if any(k in vals for k in trigger_fields):
            for rec in self:
                if rec.successor_task_id:
                    rec.successor_task_id._recalculate_schedule()
        return res

    def unlink(self):
        # Before deleting, grab the successors so we can recalculate them afterwards
        successors = self.mapped('successor_task_id')
        res = super().unlink()
        # Recalculate tasks that just lost a dependency
        for successor in successors:
            successor._recalculate_schedule()
        return res