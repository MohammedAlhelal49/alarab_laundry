from odoo import models, fields, api, _


class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    task_id = fields.Many2one(
        'project.task',
        string="Featured Task",
        help="Select a task from this project to pull its subtask progress matrix.",
        domain="[('project_id', '=', project_id), ('parent_id', '=', False)]"
    )

    progress = fields.Float(
        string="Progress",
        digits=(16, 2),
        default=0.0
    )

    task_progress_html = fields.Html(
        string="Task Progress Matrix"
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure snapshot values are generated at creation if task_id is present in vals."""
        for vals in vals_list:
            if vals.get('task_id'):
                task = self.env['project.task'].browse(vals['task_id'])
                if task.exists():
                    if 'progress' not in vals:
                        vals['progress'] = task.progress_percent
                    if 'task_progress_html' not in vals:
                        vals['task_progress_html'] = self._build_task_progress_html(task)
        return super().create(vals_list)

    @api.onchange('task_id')
    def _onchange_task_id(self):
        """Populate the snapshot fields dynamically in the view when a user selects a task."""
        if not self.task_id:
            self.progress = 0.0
            self.task_progress_html = False
            return

        # Snapshot current values from the task
        self.progress = self.task_id.progress_percent
        self.task_progress_html = self._build_task_progress_html(self.task_id)

    def _build_task_progress_html(self, task):
        """Helper method to construct the HTML checklist snapshot."""
        if not task:
            return False

        html_content = f"<h4><strong>Final Updates: {task.name}</strong></h4>"

        if task.child_ids:
            html_content += "<p>Subtask Progression Checklist:</p><ul style='list-style-type: none; padding-left: 10px;'>"
            for subtask in task.child_ids:
                checked = "checked='checked'" if subtask.progress_percent >= 100.0 else ""
                disabled = "disabled='disabled'"
                html_content += f"""
                    <li style='margin-bottom: 8px; display: flex; align-items: center;'>
                        <input type='checkbox' {checked} {disabled} style='margin-right: 10px; transform: scale(1.1);'/>
                        <span style='min-width: 250px; display: inline-block;'>{subtask.name}</span>
                        <span class='badge rounded-pill text-bg-info' style='margin-left: 15px;'>
                            {int(subtask.progress_percent)}% Complete
                        </span>
                    </li>
                """
            html_content += "</ul>"
        else:
            html_content += f"<p><em>Note: No breakdown subtasks found under '{task.name}'. Current individual task progress is {int(task.progress_percent)}%.</em></p>"

        return html_content