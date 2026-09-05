# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SubcontractorLine(models.Model):
    _name = 'job.cost.subcontractor'
    _description = 'Job Cost Sheet Subcontractor Cost'
    _order = 'id asc'

    sheet_id = fields.Many2one(
        'job.cost.sheet',
        required=True,
        ondelete='cascade'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Subcontractor',
        required=True,
        help="Subcontractor / Vendor providing this service"
    )

    description = fields.Text(string="Description")

    duration_type = fields.Selection([
        ('day', 'Day'),
        ('month', 'Month'),
        ('year', 'Year'),
    ], string="Duration Type", default='year')

    duration = fields.Float(string="Duration", default=1.0)
    price_per_duration = fields.Float(string='Cost Per Duration', default=0.0)

    cost_price_subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_cost_price_subtotal',
        store=True
    )

    @api.depends('duration', 'price_per_duration')
    def _compute_cost_price_subtotal(self):
        for rec in self:
            rec.cost_price_subtotal = rec.duration * rec.price_per_duration

    @api.constrains('sheet_id')
    def _check_max_one_subcontractor(self):
        for rec in self:
            # Check how many lines exist for this specific Job Cost Sheet
            if self.search_count([('sheet_id', '=', rec.sheet_id.id)]) > 1:
                raise ValidationError(_("You can only add a single subcontractor per Job Cost Sheet."))

    # =========================================================================
    # >>> NEW CODE — ADDED FOR SUBCONTRACTOR RETENTION FEATURE <<<
    # This field did NOT exist in the original module. It is the retention
    # percentage agreed with this subcontractor. It is copied onto the
    # generated project.task at project-creation time (see job_cost_project.py
    # action_create_project), the same way the vendor already copies
    # subcontractor_partner_id / subcontractor_subtotal. Billing itself now
    # happens from the Task form ("Subcontractor" tab), not from this line.
    # =========================================================================
    retention_percent = fields.Float(
        string="Retention (%)",
        default=0.0,
        help="Percentage withheld from the subcontractor's bill and held in "
             "the Retention Payable account until released. Copied onto the "
             "Task when the project is created."
    )

    @api.constrains('retention_percent')
    def _check_retention_percent(self):
        for rec in self:
            if rec.retention_percent < 0 or rec.retention_percent > 100:
                raise ValidationError(_(
                    "Retention percentage must be between 0 and 100 (Subcontractor: %s)."
                ) % rec.partner_id.name)

    @api.onchange('retention_percent')
    def _onchange_retention_percent(self):
        for rec in self:
            if rec.retention_percent > 100 or rec.retention_percent < 0:
                rec.retention_percent = min(max(rec.retention_percent, 0), 100)
    # <<< END NEW CODE >>>


# -------------------------------------------------------------------------
# INHERIT PARTNER MODEL TO ENFORCE INTEGRITY CONSTRAINT
# -------------------------------------------------------------------------
class ResPartner(models.Model):
    _inherit = 'res.partner'

    def unlink(self):
        """CRITICAL REQUIREMENT: Block deletion of any contact linked to a JCS line."""
        subcontractor_lines = self.env['job.cost.subcontractor'].sudo().search([
            ('partner_id', 'in', self.ids)
        ])
        if subcontractor_lines:
            linked_partners = subcontractor_lines.mapped('partner_id.name')
            raise UserError(_(
                "Operational Halt! You cannot delete the following contact(s) because they are "
                "assigned to active Job Cost Sheets: %s"
            ) % ", ".join(linked_partners))

        return super(ResPartner, self).unlink()