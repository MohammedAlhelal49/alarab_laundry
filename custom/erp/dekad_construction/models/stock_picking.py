from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    project_id = fields.Many2one('project.project', string='Project')


class StockMove(models.Model):
    _inherit = 'stock.move'

    task_id = fields.Many2one('project.task', string='Project Task')

    project_id = fields.Many2one(
        'project.project',
        related='picking_id.project_id',
        string='Project',
        store=True,
        readonly=True,
    )
