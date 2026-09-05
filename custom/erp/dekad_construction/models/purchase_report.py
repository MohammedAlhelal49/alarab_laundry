from odoo import models, fields
from odoo.tools import SQL


class PurchaseReport(models.Model):
    _inherit = 'purchase.report'

    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    task_id = fields.Many2one('project.task', string='Project Task', readonly=True)

    def _select(self):
        """Inject fields into the SELECT clause using Odoo 18 SQL wrapper."""
        return SQL(
            "%s, po.project_id as project_id, l.task_id as task_id",
            super()._select()
        )

    def _group_by(self):
        """Non-aggregated fields MUST be added to the GROUP BY clause in PostgreSQL."""
        return SQL(
            "%s, po.project_id, l.task_id",
            super()._group_by()
        )
