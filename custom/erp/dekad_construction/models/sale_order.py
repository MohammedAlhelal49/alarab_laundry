# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True,
    )

    job_cost_project_id = fields.Many2one(
        'job.cost.project',
        string="Job Cost Project Source",
        ondelete='set null'
    )

    def action_confirm(self):
        """
        Override Odoo core confirmation process to ensure that validating
        the sale order triggers immediate structural state updates back on the parent JCP.
        """
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.job_cost_project_id:
                # Force immediate recalculation of the dependency constraint mapping
                order.job_cost_project_id._compute_has_confirmed_so()
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    currency_id = fields.Many2one(
        related='order_id.currency_id',
        store=True,
        readonly=True
    )
