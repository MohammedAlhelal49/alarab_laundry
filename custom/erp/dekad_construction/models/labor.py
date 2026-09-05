# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# =========================================================================
# 1. EXTERNAL LABOR (Subcontractors / Daily / Period-based Workers)
# =========================================================================
class LaborExternal(models.Model):
    _name = 'labor.external'
    _description = 'External Labor Allocation'
    _order = 'id desc'

    sheet_id = fields.Many2one('job.cost.sheet', required=True, ondelete='cascade')
    profession_id = fields.Many2one('labor.tag', string='Profession', required=True, ondelete='restrict')
    description = fields.Char(string='Scope / Description')

    labor_count = fields.Integer(string='No. of Laborers', default=1, required=True)

    period_type = fields.Selection([
        ('day', 'Days'),
        ('month', 'Months'),
        ('year', 'Years')
    ], string='Period Unit', default='day', required=True)

    period_count = fields.Float(string='Duration', default=1.0, required=True)
    unit_rate = fields.Monetary(string='Rate per Period', default=0.0, required=True)
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True)

    currency_id = fields.Many2one('res.currency', related='sheet_id.currency_id')

    @api.depends('period_count', 'unit_rate')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.labor_count * rec.period_count * rec.unit_rate

    @api.constrains('period_count', 'labor_count')
    def _check_positive_values(self):
        for rec in self:
            if rec.period_count <= 0:
                raise ValidationError(_("External labor duration must be greater than zero."))
            if rec.labor_count <= 0:
                raise ValidationError(_("The number of laborers must be greater than zero."))


# =========================================================================
# 2. INTERNAL LABOR (Company HR Employees)
# =========================================================================
class LaborInternal(models.Model):
    _name = 'labor.internal'
    _description = 'Internal HR Employee Allocation'
    _order = 'id desc'

    sheet_id = fields.Many2one('job.cost.sheet', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='HR Employee', required=True, ondelete='restrict')
    job_title = fields.Char(string='Job Title', related='employee_id.job_title', readonly=True)
    description = fields.Char(string='Assigned Task')

    # Pulled from HR, but left as a normal monetary field so estimators can override it if needed
    monthly_salary = fields.Monetary(string='Basic Monthly Salary', default=0.0, required=True)

    # Proportion of the employee's monthly time dedicated to this specific job sheet
    allocated_months = fields.Float(string='Allocated Months', default=1.0, required=True)
    subtotal = fields.Monetary(string='Subtotal Cost', compute='_compute_subtotal', store=True)

    currency_id = fields.Many2one('res.currency', related='sheet_id.currency_id')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            if not rec.employee_id:
                rec.monthly_salary = 0.0
                continue

            # Safely check if the active DB uses the 'hr.contract' app to grab official wages
            if 'hr.contract' in self.env:
                contract = self.env['hr.contract'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('state', '=', 'open')
                ], limit=1)
                rec.monthly_salary = contract.wage if contract else 0.0
            else:
                rec.monthly_salary = 0.0

    @api.depends('monthly_salary', 'allocated_months')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.monthly_salary * rec.allocated_months

    @api.constrains('allocated_months')
    def _check_positive_allocation(self):
        for rec in self:
            if rec.allocated_months <= 0:
                raise ValidationError(_("Allocated months for internal employees must be greater than zero."))


# =========================================================================
# 3. LABOR TAGS (Preserved as requested)
# =========================================================================
class LaborTag(models.Model):
    _name = "labor.tag"
    _description = "Labor Tag"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True)
    scope = fields.Text(string="Scope/Description")
    sequence = fields.Integer(default=10)