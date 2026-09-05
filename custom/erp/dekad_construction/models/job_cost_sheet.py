from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta


class JobCostSheet(models.Model):
    _name = 'job.cost.sheet'
    _description = 'Job Cost Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(string='Sequence #')
    boq_code = fields.Char(string="BoQ Code")

    is_locked = fields.Boolean(
        string="Locked",
        compute='_compute_is_locked',
        copy=False,
        store=False,
        help="If True, this Job Cost Sheet is locked from editing until all prior steps are confirmed."
    )

    bypass_validation = fields.Boolean(string="Bypass Validation", store=False, default=False)

    job_cost_project_id = fields.Many2one(
        'job.cost.project',
        string="Job Cost Project",
        ondelete='cascade',
        required=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related="job_cost_project_id.partner_id",
        store=True,
        readonly=True
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string="Responsible (HR)",
        related="job_cost_project_id.employee_id",
        store=True,
        readonly=True
    )

    percentage = fields.Integer(
        string="Percentage (%)",
        help="Share of this Job Cost Sheet over the whole construction project (0-100)",
        default=0
    )

    total_project_percentage = fields.Float(
        string="Total Accumulated Project Share",
        compute="_compute_total_project_percentage",
        help="Total combined allocation percentage across all sibling cost sheets under this project."
    )

    lead_deadline = fields.Date(
        string="Project Deadline",
        readonly=True,
        help="Deadline copied from the CRM Lead at creation time."
    )

    quantity = fields.Float(string="Quantity", default=1.0)
    requirement_note = fields.Text(string="Client Requirement Notes")

    material_ids = fields.One2many('material', 'sheet_id', string='Materials')
    equipment_asset_ids = fields.One2many(
        'equipment', 'sheet_id',
        string='Asset Equipment Lines',
        domain=[('equipment_ownership_type', '=', 'asset')]
    )
    equipment_rental_ids = fields.One2many(
        'equipment', 'sheet_id',
        string='Rental Equipment Lines',
        domain=[('equipment_ownership_type', '=', 'rental')]
    )
    equipment_ids = fields.One2many('equipment', 'sheet_id', string='Equipment')
    external_labor_ids = fields.One2many('labor.external', 'sheet_id', string="External Labor Lines")
    internal_labor_ids = fields.One2many('labor.internal', 'sheet_id', string="Internal Labor Lines")
    overhead_ids = fields.One2many('job.cost.overhead', 'sheet_id', string='Overhead')
    subcontractor_ids = fields.One2many('job.cost.subcontractor', 'sheet_id', string='Subcontractor')

    def _get_default_uom_id(self):
        return self.env.ref('uom.uom_square_meter', raise_if_not_found=False)

    uom_id = fields.Many2one('uom.uom', string="Unit of Measure", default=_get_default_uom_id,
                             help="Default unit of measure is square meters (m²).")

    jcp_creation_date = fields.Date(
        string="JCP Creation Date",
        related="job_cost_project_id.creation_date",
        readonly=True
    )

    date_start = fields.Date(string='Expected Start Date')
    date_end = fields.Date(string='Expected End Date')

    boq_expected_duration_days = fields.Integer(
        string="BoQ Expected Duration (Days)",
        compute="_compute_boq_expected_duration_days",
        inverse="_inverse_boq_expected_duration_days",
        store=True,
    )

    # -----------------------------------------------------
    # Cost & Pricing Summary (Optimized & Merged Chain)
    # -----------------------------------------------------
    material_total = fields.Float(compute="_compute_totals", store=True)
    equipment_total = fields.Float(compute="_compute_totals", store=True)

    total_equipment_cost = fields.Float(
        string="Total Equipment Cost",
        compute="_compute_total_equipment_cost",
        store=True
    )

    total_external_labor = fields.Monetary(string="Total External Labor", compute="_compute_labor_totals", store=True)
    total_internal_labor = fields.Monetary(string="Total Internal Labor", compute="_compute_labor_totals", store=True)
    labor_total = fields.Monetary(string="Grand Total Labor", compute="_compute_labor_totals", store=True)
    overhead_total = fields.Float(compute="_compute_totals", store=True)
    subcontractor_total = fields.Float(compute="_compute_totals", store=True)

    base_cost_total = fields.Float(
        string="Base Cost Total",
        compute="_compute_totals",
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    risk_percent = fields.Float(string="Risk %", default=0.0)
    risk_amount = fields.Float(compute="_compute_totals", store=True)

    margin_percent = fields.Float(string="Margin %", default=0.0)
    margin_amount = fields.Float(compute="_compute_totals", store=True)

    final_selling_price = fields.Float(
        string="Final Selling Price",
        compute="_compute_totals",
        store=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        # Check if the execution context is explicitly instructed to skip this validation
        if not self.env.context.get('bypass_costing_check'):
            for vals in vals_list:
                project_id = vals.get('job_cost_project_id')
                if project_id:
                    if isinstance(project_id, str) or isinstance(project_id, models.NewId):
                        raise ValidationError(
                            _("Cannot attach a sheet to an unsaved project context. Please save your main card first."))

                    project = self.env['job.cost.project'].browse(project_id)
                    if project.exists() and project.state != 'costing':
                        raise UserError(
                            _("You can only add new Job Cost Sheets when the Project layout state is in 'Costing' mode."))

        return super().create(vals_list)

    def unlink(self):
        for rec in self:
            if rec.job_cost_project_id and rec.job_cost_project_id.state != 'costing' and rec.job_cost_project_id.state != 'draft':
                raise UserError(
                    _("You cannot drop lines while the parent project setup is locked outside Costing phases."))

            if self.filtered('is_locked'):
                raise UserError(_("You cannot delete a locked job cost sheet until prior sheets are confirmed."))

        return super().unlink()

    @api.depends("date_start", "date_end")
    def _compute_boq_expected_duration_days(self):
        for record in self:
            if record.date_start and record.date_end:
                delta = record.date_end - record.date_start
                record.boq_expected_duration_days = delta.days
            else:
                record.boq_expected_duration_days = 0

    def _inverse_boq_expected_duration_days(self):
        for record in self:
            if record.date_start and record.boq_expected_duration_days:
                record.date_end = record.date_start + timedelta(days=record.boq_expected_duration_days)

        # ---------------------------------------------------------
        # HARD BACKEND CONSTRAINTS (Database Layer Security)
        # ---------------------------------------------------------
        @api.constrains('date_start', 'date_end')
        def _check_jcp_timeline_boundaries(self):
            """Hard database block preventing dates from slipping outside the macro JCP window."""
            for rec in self:
                # 1. Base chronological alignment check
                if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                    raise ValidationError(_("Validation Error: The End Date cannot be before the Start Date."))

                # 2. Check against parent JCP Creation Date
                parent = rec.job_cost_project_id
                if parent and parent.creation_date and rec.date_start:
                    if rec.date_start < parent.creation_date:
                        raise ValidationError(_(
                            "Timeline Violation: The start date (%s) for item '%s' cannot be "
                            "earlier than the macro JCP Creation Date (%s)."
                        ) % (rec.date_start, rec.name, parent.creation_date))

                # 3. Check against macro JCP Deadline window
                if rec.date_end and rec.lead_deadline:
                    if rec.date_end > rec.lead_deadline:
                        raise ValidationError(_(
                            "Timeline Violation: The expected end date (%s) for item '%s' "
                            "exceeds the client's strict project deadline (%s)."
                        ) % (rec.date_end, rec.name, rec.lead_deadline))

        # ---------------------------------------------------------
        # DYNAMIC UI ONCHANGES (User Experience Layer)
        # ---------------------------------------------------------
        @api.onchange('date_start', 'date_end')
        def _onchange_dates(self):
            """Calculates duration dynamically and safely handles micro anomalies."""
            if self.date_start and self.date_end:
                if self.date_end < self.date_start:
                    self.date_end = self.date_start
                    return {
                        'warning': {
                            'title': _("Invalid Date Sequence"),
                            'message': _("End date cannot be before start date. Reverting date markers to sync.")
                        }
                    }
                self.boq_expected_duration_days = (self.date_end - self.date_start).days
            else:
                self.boq_expected_duration_days = 0

    @api.onchange('boq_expected_duration_days')
    def _onchange_duration(self):
        if self.date_start and self.boq_expected_duration_days:
            self.date_end = self.date_start + timedelta(days=self.boq_expected_duration_days)

    @api.constrains('date_start', 'date_end')
    def _check_jcp_window_hard_constraints(self):
        """Enforces absolute timeline guardrails against the parent JCP window."""
        for rec in self:
            parent = rec.job_cost_project_id
            if not parent:
                continue

            # 1. Hard block if the start date slips before the JCP creation milestone
            if rec.date_start and parent.creation_date and rec.date_start < parent.creation_date:
                raise ValidationError(_(
                    "Validation Error: The entered start date (%s) for item '%s' is "
                    "earlier than the permitted macro JCP creation date (%s)."
                ) % (rec.date_start, rec.name, parent.creation_date))

            # 2. Hard block if the end date slips past the client's contract deadline
            if rec.date_end and rec.lead_deadline and rec.date_end > rec.lead_deadline:
                raise ValidationError(_(
                    "Validation Error: The expected end date (%s) for item '%s' "
                    "exceeds the client's strict project deadline (%s)."
                ) % (rec.date_end, rec.name, rec.lead_deadline))

    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(_("Quantity must be greater than 0."))

    @api.onchange('percentage')
    def _onchange_percentage(self):
        for rec in self:
            if rec.percentage > 100 or rec.percentage < 0:
                rec.percentage = min(max(rec.percentage, 0), 100)
                return {
                    'warning': {
                        'title': _("Invalid Percentage"),
                        'message': _("Percentage must be between 0 and 100."),
                    }
                }

    @api.constrains('percentage', 'job_cost_project_id')
    def _check_project_percentage_limit(self):
        """Guarantees JCS percentages never exceed 100% across the parent JCP."""

        # 1. Individual Record Validation
        for sheet in self:
            if sheet.percentage < 0:
                raise ValidationError(_("Validation Error: Percentage cannot be negative (Sheet: %s).") % sheet.name)
            if sheet.percentage > 100:
                raise ValidationError(
                    _("Validation Error: A single Job Cost Sheet cannot exceed 100%% (Sheet: %s).") % sheet.name)

        # 2. Aggregate Parent Validation (Optimized for bulk operations)
        # We extract unique parent projects affected by this transaction
        affected_projects = self.mapped('job_cost_project_id').filtered(lambda p: p.id)

        for project in affected_projects:
            # Sum the percentage of all sheets linked to this specific parent
            total_percentage = sum(project.job_cost_sheet_ids.mapped('percentage'))

            if total_percentage > 100:
                raise ValidationError(_(
                    "Percentage Overflow: The total percentage of all Job Cost Sheets "
                    "under the parent project '%s' is %s%%, which exceeds the 100%% limit. "
                    "Please adjust the individual sheet shares."
                ) % (project.display_name, total_percentage))

    @api.depends('job_cost_project_id', 'job_cost_project_id.job_cost_sheet_ids.percentage')
    def _compute_total_project_percentage(self):
        """Calculates the total aggregate percentage allocated under the parent project."""
        for rec in self:
            if rec.job_cost_project_id:
                # Sum up all sibling sheets sharing this parent project layout
                rec.total_project_percentage = sum(
                    rec.job_cost_project_id.job_cost_sheet_ids.mapped('percentage')
                )
            else:
                rec.total_project_percentage = 0.0

    @api.depends('sequence', 'job_cost_project_id.job_cost_sheet_ids.state')
    def _compute_is_locked(self):
        for rec in self:
            '''
            if not rec.job_cost_project_id:
                rec.is_locked = False
                continue

            prev = rec.job_cost_project_id.job_cost_sheet_ids.filtered(
                lambda s: s.sequence < (rec.sequence or 0)
            )
            if prev and any(s.state != 'confirmed' for s in prev):
                rec.is_locked = True
            else:
                rec.is_locked = False
                '''
            rec.is_locked = False

    def write(self, vals):
        # We only block the write if the user is explicitly trying to modify a record
        # that evaluates to locked in the current interface view state.
        locked = self.filtered('is_locked')
        if locked:
            allowed_when_locked = {'state', 'message_post'}
            for rec in locked:
                if any(k not in allowed_when_locked for k in vals.keys()):
                    raise UserError(_("This job cost sheet is locked until previous steps are confirmed."))

        return super().write(vals)

    @api.depends('equipment_asset_ids.cost_price_subtotal', 'equipment_rental_ids.cost_price_subtotal')
    def _compute_total_equipment_cost(self):
        for sheet in self:
            sheet.total_equipment_cost = (
                    sum(sheet.equipment_asset_ids.mapped('cost_price_subtotal')) +
                    sum(sheet.equipment_rental_ids.mapped('cost_price_subtotal'))
            )

    @api.depends('external_labor_ids.subtotal', 'internal_labor_ids.subtotal')
    def _compute_labor_totals(self):
        for sheet in self:
            ext = sum(sheet.external_labor_ids.mapped('subtotal'))
            int_lab = sum(sheet.internal_labor_ids.mapped('subtotal'))

            sheet.total_external_labor = ext
            sheet.total_internal_labor = int_lab
            sheet.labor_total = ext + int_lab

    # -------------------------------------------------------------
    # Unified Master Calculation
    # -------------------------------------------------------------
    @api.depends(
        'material_ids.cost_price_subtotal',
        'equipment_asset_ids.cost_price_subtotal',  # Listen to specific Asset view
        'equipment_rental_ids.cost_price_subtotal',  # Listen to specific Rental view
        'external_labor_ids.subtotal',
        'internal_labor_ids.subtotal',
        'overhead_ids.cost_price_subtotal',
        'subcontractor_ids.cost_price_subtotal',
        'risk_percent', 'margin_percent'
    )
    def _compute_totals(self):
        for rec in self:
            rec.material_total = sum(rec.material_ids.mapped('cost_price_subtotal'))

            # Aggregate equipment costs manually from both separate tables
            rec.equipment_total = (
                    sum(rec.equipment_asset_ids.mapped('cost_price_subtotal')) +
                    sum(rec.equipment_rental_ids.mapped('cost_price_subtotal'))
            )

            rec.overhead_total = sum(rec.overhead_ids.mapped('cost_price_subtotal'))
            rec.subcontractor_total = sum(rec.subcontractor_ids.mapped('cost_price_subtotal'))

            rec.total_external_labor = sum(rec.external_labor_ids.mapped('subtotal'))
            rec.total_internal_labor = sum(rec.internal_labor_ids.mapped('subtotal'))
            rec.labor_total = rec.total_external_labor + rec.total_internal_labor

            rec.base_cost_total = (
                    rec.material_total +
                    rec.equipment_total +
                    rec.labor_total +
                    rec.overhead_total +
                    rec.subcontractor_total
            )

            rec.risk_amount = rec.base_cost_total * (rec.risk_percent / 100.0)
            subtotal = rec.base_cost_total + rec.risk_amount

            rec.margin_amount = subtotal * (rec.margin_percent / 100.0)
            rec.final_selling_price = subtotal + rec.margin_amount

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_draft(self):
        self.write({'state': 'draft'})
