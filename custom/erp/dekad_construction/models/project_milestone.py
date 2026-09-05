from odoo import models, fields, api, _
from datetime import timedelta, datetime
from odoo.exceptions import ValidationError, UserError


# -----------------------------------------------------
# Extend the project.task module to link back and hold progress
# -----------------------------------------------------
class ProjectTask(models.Model):
    _inherit = 'project.task'

    progress_percent = fields.Float(
        string='Progress (%)',
        default=0.0,
        compute='_compute_progress_percent',
        store=True,
        readonly=False,
        help="Manually set the progress, or if subtasks exist, it will automatically average their progress."
    )

    # -----------------------------------------------------
    # Duration
    # -----------------------------------------------------
    planned_start_date = fields.Date(
        string="Planned Start Date"
    )

    planned_end_date = fields.Date(
        string="Planned End Date",
        compute="_compute_planned_end_date",
        store=True
    )

    planned_duration = fields.Integer(
        string="Planned Duration (Days)",
        help="Expected task duration in days",
        default=1,
    )

    # -----------------------------------------------------
    # Link dependencies to tasks
    # -----------------------------------------------------
    predecessor_dependency_ids = fields.One2many(
        'project.task.dependency',
        'successor_task_id',
        string="Predecessors"
    )

    successor_dependency_ids = fields.One2many(
        'project.task.dependency',
        'predecessor_task_id',
        string="Successors"
    )

    # -----------------------------------------------------
    # Aggregate actual costs on task
    # -----------------------------------------------------
    purchase_line_ids = fields.One2many(
        'purchase.order.line',
        'task_id',
        string='Purchase Lines'
    )

    account_move_line_ids = fields.One2many(
        'account.move.line',
        'task_id',
        string='Journal Items'
    )

    expense_ids = fields.One2many(
        'hr.expense',
        'task_id',
        string='Expenses'
    )

    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )

    estimated_cost_total = fields.Monetary(
        string="Estimated Cost",
        help="Estimated cost transferred from Job Cost Sheet at project creation.",
        currency_field="company_currency_id",
    )

    actual_cost_total = fields.Monetary(
        string='Actual Total Cost',
        compute='_compute_actual_cost_total',
        currency_field='company_currency_id',
        store=True
    )

    actual_cost_total_recursive = fields.Monetary(
        string="Total Actual Cost (Including Subtasks)",
        compute="_compute_actual_cost_total_recursive",
        store=True,
        recursive=True,
        currency_field="company_currency_id",
    )

    cost_variance = fields.Monetary(
        string="Cost Variance",
        compute="_compute_cost_variance",
        store=True,
        currency_field="company_currency_id",
    )

    # -----------------------------------------------------
    # Subcontractor fields
    # -----------------------------------------------------
    subcontractor_partner_id = fields.Many2one(
        'res.partner',
        string='Subcontractor',
        readonly=True,
        help="Subcontractor assigned from the Job Cost Sheet."
    )

    subcontractor_subtotal = fields.Float(
        string='Subcontractor Cost',
        readonly=True
    )

    # =========================================================================
    # >>> NEW CODE — ADDED FOR SUBCONTRACTOR RETENTION & BILLING FEATURE <<<
    # Everything below (down to "END NEW CODE") did NOT exist in the vendor's
    # module. subcontractor_retention_percent mirrors how the vendor already
    # copies subcontractor_partner_id / subcontractor_subtotal onto the Task
    # at project-creation time (see job_cost_project.py action_create_project).
    # action_create_subcontractor_bill() is the new "Create Bill" button shown
    # on the Task's "Subcontractor" tab: it bills (Task progress % × estimated
    # subcontractor cost), net of retention, using the two products configured
    # in Settings (Accounting > Vendor Bills > Subcontractor Billing).
    # =========================================================================
    subcontractor_retention_percent = fields.Float(
        string='Retention (%)',
        readonly=True,
        help="Retention percentage copied from the Job Cost Sheet's subcontractor "
             "line when the project was created."
    )

    # ---- New field: tracks the progress % already billed, to enforce cumulative billing ----
    last_billed_progress_percent = fields.Float(
        string='Last Billed Progress (%)',
        default=0.0,
        readonly=True,
        copy=False,
        help="The subcontractor progress percentage that was already billed. "
             "The next bill only covers the increase over this value."
    )

    # ---- New: count of bills already generated for this task, drives the "Bills" button ----
    subcontractor_bill_count = fields.Integer(
        compute='_compute_subcontractor_bill_count',
    )

    @api.depends('last_billed_progress_percent')
    def _compute_subcontractor_bill_count(self):
        # account.move has no direct link back to the task, so we search via
        # the invoice line's task_id (set on the Gross line by our billing action).
        for task in self:
            task.subcontractor_bill_count = self.env['account.move'].search_count([
                ('invoice_line_ids.task_id', '=', task.id),
            ])

    def action_open_subcontractor_bills(self):
        """Opens the list of Vendor Bills already generated for this task's subcontractor."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subcontractor Bills'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('invoice_line_ids.task_id', '=', self.id)],
            'target': 'current',
        }

    # ---- New: the auto-created Subcontracting Service product for THIS task,
    # created on the first bill and reused for every later bill on this task ----
    subcontractor_service_product_id = fields.Many2one(
        'product.product',
        string='Subcontracting Service Product',
        readonly=True,
        copy=False,
        help="Auto-created the first time a bill is generated for this task's "
             "subcontractor, named after the task. Reused for every later bill "
             "on this task."
    )

    def _get_or_create_subcontractor_service_product(self):
        """Return the Service product to use as the Gross invoice line for this
        task's subcontractor. Created once (named after the task, no purchase
        taxes, Expense Account from Settings) and reused afterwards."""
        self.ensure_one()

        if self.subcontractor_service_product_id:
            return self.subcontractor_service_product_id

        service_account = self.env.company.subcontractor_service_account_id
        if not service_account:
            raise UserError(_(
                "Please configure the Subcontractor Service Account first "
                "(Settings > Accounting > Vendor Bills > Subcontractor Billing)."
            ))

        # ---- Odoo context leak fix: the calling context (task/project form)
        # carries 'default_project_id', and product.template happens to have
        # a field with the exact same name (used for a totally different
        # "generate a project on sale" feature). Without clearing it, Odoo
        # would apply that default here and trip a validation error
        # ("product should not have a project..."). Explicitly clear it.
        product = self.env['product.product'].with_context(
            default_project_id=False,
            default_project_template_id=False,
        ).create({
            # Prefixed to avoid an exact-name clash with the CRM requirement's
            # original product (Task.name is copied from that product's name).
            'name': _("Subcontracting: %s") % self.name,
            'type': 'service',
            'purchase_ok': True,
            'sale_ok': False,
            'company_id': self.company_id.id,
            'property_account_expense_id': service_account.id,
            # No taxes at all on this product (per requirement)
            'supplier_taxes_id': [(6, 0, [])],
            'taxes_id': [(6, 0, [])],
        })
        self.subcontractor_service_product_id = product.id
        return product

    def action_create_subcontractor_bill(self):
        """Generate a draft Vendor Bill for this task's subcontractor.
        Cumulative logic: only the NEW progress since the last bill is billed
        (e.g. billed at 30% before, now at 60% -> this bill covers 30%->60%,
        not the full 60%). Blocks the action entirely if progress hasn't
        increased since the last bill."""
        self.ensure_one()

        if not self.subcontractor_partner_id:
            raise UserError(_(
                "This task has no subcontractor assigned."
            ))

        retention_product = self.env.company.retention_product_id
        if not retention_product:
            raise UserError(_(
                "Please configure the Retention product first "
                "(Settings > Accounting > Vendor Bills > Subcontractor Billing)."
            ))

        # ---- New: get (or create, on the very first bill) this task's own
        # Subcontracting Service product ----
        service_product = self._get_or_create_subcontractor_service_product()

        # ---- New: block if there is no new progress since the last bill ----
        if self.progress_percent <= self.last_billed_progress_percent:
            raise UserError(_(
                "Nothing to bill: current progress (%s%%) is not higher than the "
                "progress already billed (%s%%)."
            ) % (self.progress_percent, self.last_billed_progress_percent))

        # ---- Gross amount: Quantity = only the NEW progress since last bill
        # (e.g. previously billed 30%, now at 60% -> quantity covers 0.3, not 0.6),
        # Price Unit = the full contract value.
        # NOTE: Quantity is stored at the Product Unit of Measure decimal precision
        # (Settings > Technical > Decimal Accuracy). For non-round percentages
        # (e.g. 33.33%), increase that precision to avoid rounding differences.
        new_progress = self.progress_percent - self.last_billed_progress_percent
        quantity = new_progress / 100.0
        gross_amount = self.subcontractor_subtotal * quantity
        retention_amount = gross_amount * (self.subcontractor_retention_percent / 100.0)

        # task_id is set only on the Gross line, so this bill counts towards
        # the task's actual_cost_total (Journal Items aggregation above),
        # matching estimated_cost_total for a fair estimate-vs-actual comparison.
        invoice_line_vals = [
            (0, 0, {
                'product_id': service_product.id,
                'name': _("%s - progress %s%% to %s%%") % (
                    self.name, self.last_billed_progress_percent, self.progress_percent,
                ),
                'quantity': quantity,
                'price_unit': self.subcontractor_subtotal,
                'task_id': self.id,
            }),
        ]
        if retention_amount:
            invoice_line_vals.append((0, 0, {
                'product_id': retention_product.id,
                'name': _("Retention withheld (%s%%)") % self.subcontractor_retention_percent,
                'quantity': 1.0,
                'price_unit': -retention_amount,
            }))

        move_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.subcontractor_partner_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_line_ids': invoice_line_vals,
        }
        if self.project_id:
            move_vals['project_id'] = self.project_id.id

        move = self.env['account.move'].create(move_vals)

        # ---- New: remember how much progress has now been billed ----
        self.last_billed_progress_percent = self.progress_percent

        return {
            'type': 'ir.actions.act_window',
            'name': _('Subcontractor Bill'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
            'target': 'current',
        }
    # <<< END NEW CODE >>>

    # -----------------------------------------------------
    # Restrict progress and reflect upon the subtasks
    # -----------------------------------------------------
    @api.onchange('progress_percent')
    def _onchange_progress_percent(self):
        for rec in self:
            if rec.progress_percent > 100 or rec.progress_percent < 0:
                rec.progress_percent = min(max(rec.progress_percent, 0), 100)
                return {
                    'warning': {
                        'title': _("Invalid Percentage"),
                        'message': _("Percentage must be between 0 and 100."),
                    }
                }

    @api.depends('child_ids', 'child_ids.progress_percent')
    def _compute_progress_percent(self):
        for task in self:
            if task.child_ids:
                # Sum the progress of all direct subtasks
                total_progress = sum(task.child_ids.mapped('progress_percent'))
                # Calculate the average
                task.progress_percent = total_progress / len(task.child_ids)
            else:
                # If there are no subtasks, preserve whatever was manually typed in
                task.progress_percent = task.progress_percent or 0.0

    # A helper technical field to handle layout logic safely
    is_progress_readonly = fields.Boolean(
        compute="_compute_is_progress_readonly",
        store=False
    )

    @api.depends('child_ids', 'parent_id')
    def _compute_is_progress_readonly(self):
        for task in self:
            # Lock ONLY if it is a parent task that has children beneath it
            if task.child_ids and not task.parent_id:
                task.is_progress_readonly = True
            else:
                task.is_progress_readonly = False

    @api.constrains('parent_id')
    def _check_parent_progress_for_subtasks(self):
        """Ensures subtasks can only be initialized if the parent task is clean (0% progress)."""
        for task in self:
            # If this record is being designated as a subtask
            if task.parent_id:
                # Check the progress of the target parent task
                if task.parent_id.progress_percent != 0:
                    raise ValidationError(_(
                        "Structure Restriction: You cannot add subtasks to the parent task '%s' "
                        "because its current progress is at %s%%.\n\n"
                        "Subtasks can only be introduced when a task's progress is exactly 0%%."
                    ) % (task.parent_id.name, task.parent_id.progress_percent))

    def unlink(self):
        """Intercept task deletions and block them if progress has been made."""
        for task in self:
            if task.progress_percent > 0.0:
                raise UserError(_(
                    "Operational Halt! You cannot delete the task '%s' because it has active "
                    "progress logged (%s%%). Please set the progress to 0%% or archive the task instead."
                ) % (task.name, task.progress_percent))

        # Execute core framework removal safely if no progress is found
        return super(ProjectTask, self).unlink()

    # -----------------------------------------------------
    # Restrict subtask dates and deadline
    # -----------------------------------------------------
    @api.onchange('parent_id')
    def _onchange_parent_id_inheritance(self):
        if self.parent_id:
            # Inherit the start date
            if self.parent_id.planned_start_date:
                self.planned_start_date = self.parent_id.planned_start_date

            # Inherit deadline
            if self.parent_id.date_deadline:
                self.date_deadline = self.parent_id.date_deadline

    @api.constrains('date_deadline', 'parent_id', 'child_ids')
    def _check_deadline_hierarchy(self):
        for task in self:
            # Check 1: If this is a subtask, is it later than the parent?
            if task.parent_id and task.parent_id.date_deadline and task.date_deadline:
                if task.date_deadline > task.parent_id.date_deadline:
                    raise ValidationError(_(
                        "Deadline Error: The subtask '%(task_name)s' cannot end after its parent task '%(parent_name)s' (%(parent_deadline)s).",
                        task_name=task.name,
                        parent_name=task.parent_id.name,
                        parent_deadline=task.parent_id.date_deadline,
                    ))

            # Check 2: If this is a parent, did we move it earlier than existing subtasks?
            if task.child_ids and task.date_deadline:
                # We search for any child that has a deadline later than the new parent deadline
                offending_subtask = task.child_ids.filtered(
                    lambda s: s.date_deadline and s.date_deadline > task.date_deadline
                )
                if offending_subtask:
                    # Pointing out the first subtask that causes the conflict
                    raise ValidationError(_(
                        "Deadline Error: The parent deadline (%(parent_deadline)s) cannot be earlier than subtask '%(subtask_name)s' (%(subtask_deadline)s).",
                        parent_deadline=task.date_deadline,
                        subtask_name=offending_subtask[0].name,
                        subtask_deadline=offending_subtask[0].date_deadline,
                    ))

    @api.onchange('date_deadline', 'project_id')
    def _onchange_deadline_warning(self):
        for rec in self:
            if rec.date_deadline and rec.project_id and rec.project_id.date:
                # 1. Normalize Task Deadline to a date object
                task_date = rec.date_deadline
                if isinstance(task_date, datetime):
                    task_date = task_date.date()

                # 2. Normalize Project Deadline to a date object
                project_date = rec.project_id.date
                if isinstance(project_date, datetime):
                    project_date = project_date.date()

                # 3. Now compare apples to apples
                if task_date > project_date:
                    return {
                        'warning': {
                            'title': _("Project Deadline Exceeded"),
                            'message': _(
                                "The task's deadline (%(task_end)s) exceeds the project's "
                                "official deadline (%(project_end)s).\n\n"
                                "Please verify if this extension is acceptable."
                            ) % {
                                           'task_end': task_date,
                                           'project_end': project_date,
                                       }
                        }
                    }

    # -----------------------------------------------------
    # Date inheritance
    # -----------------------------------------------------
    # 1. Inheritance: Populate dates when a parent is selected
    @api.model
    def default_get(self, fields_list):
        """ Inherit dates from parent task when creating via 'Add a line' or 'Create' button """
        res = super(ProjectTask, self).default_get(fields_list)

        # Check if we are creating a subtask (parent_id is usually in context)
        parent_id = res.get('parent_id') or self.env.context.get('default_parent_id')

        if parent_id:
            parent = self.browse(parent_id)
            if 'planned_start_date' in fields_list and parent.planned_start_date:
                res.update({'planned_start_date': parent.planned_start_date})
            if 'planned_duration' in fields_list and parent.planned_duration:
                res.update({'planned_duration': parent.planned_duration})
        return res

    # 2. Inheritance: Populate dates when a new subtask is created
    @api.onchange('name')  # Triggered when the user starts typing the task name
    def _onchange_name_inherit_dates(self):
        for rec in self:
            # If we have a parent but no dates yet
            if rec.parent_id and not rec.planned_start_date:
                rec.planned_start_date = rec.parent_id.planned_start_date
                rec.planned_duration = rec.parent_id.planned_duration

    # 3. Validation: Prevent subtask from exceeding parent duration
    @api.constrains('planned_end_date', 'parent_id')
    def _check_subtask_dates_limit(self):
        for task in self:
            if task.parent_id and task.planned_end_date and task.parent_id.planned_end_date:
                if task.planned_end_date > task.parent_id.planned_end_date:
                    raise ValidationError(_(
                        "The subtask '%s' cannot have a deadline later than its parent task '%s' (%s)."
                    ) % (task.name, task.parent_id.name, task.parent_id.planned_end_date))

    # 4. Validation: Prevent start date from being earlier than parent
    @api.constrains('planned_start_date', 'parent_id')
    def _check_subtask_start_limit(self):
        for task in self:
            if task.parent_id and task.planned_start_date and task.parent_id.planned_start_date:
                if task.planned_start_date < task.parent_id.planned_start_date:
                    raise ValidationError(_(
                        "The subtask '%s' cannot start before its parent task (%s)."
                    ) % (task.name, task.parent_id.planned_start_date))

    # -----------------------------------------------------
    # Scheduling and dependencies
    # -----------------------------------------------------
    @api.depends('planned_start_date', 'planned_duration')
    def _compute_planned_end_date(self):
        for task in self:
            if task.planned_start_date and task.planned_duration:
                task.planned_end_date = task.planned_start_date + timedelta(days=task.planned_duration)
            else:
                task.planned_end_date = False

    def _recalculate_schedule(self):
        for task in self:
            if not task.planned_duration:
                continue

            constraint_dates = []

            for dep in task.predecessor_dependency_ids:
                pred = dep.predecessor_task_id
                lag = timedelta(days=dep.lag_days or 0)

                # 1. Finish to Start
                if dep.dependency_type == 'fs':
                    if pred.planned_end_date:
                        constraint_dates.append(pred.planned_end_date + lag)

                # 2. Finish to Finish
                elif dep.dependency_type == 'ff':
                    if pred.planned_end_date:
                        constraint_dates.append(
                            pred.planned_end_date + lag - timedelta(days=task.planned_duration)
                        )

                # 3. Start to Start
                elif dep.dependency_type == 'ss':
                    if pred.planned_start_date:
                        # Successor's earliest start is Predecessor's start + lag
                        constraint_dates.append(pred.planned_start_date + lag)

            if constraint_dates:
                new_start = max(constraint_dates)
                # Only write if it actually changed to save database queries
                if task.planned_start_date != new_start:
                    task.planned_start_date = new_start

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        # Pass a context flag to prevent infinite recursion
        tasks.with_context(skip_subtask_deps=True)._auto_link_subtask_dependencies()
        return tasks

    def write(self, vals):
        res = super().write(vals)

        # 1. Schedule Propagation
        # Only trigger if we aren't ALREADY propagating, preventing reset of the 'visited' set
        if not self.env.context.get('is_propagating'):
            if any(k in vals for k in ['planned_start_date', 'planned_duration']):
                # Pass a context flag so subsequent writes don't trigger new propagations
                self.with_context(is_propagating=True)._propagate_schedule_forward()

        # 2. Subtask Links
        if not self.env.context.get('skip_subtask_deps'):
            if 'depend_on_ids' in vals or 'parent_id' in vals:
                self.with_context(skip_subtask_deps=True)._auto_link_subtask_dependencies()

        return res

    def _propagate_schedule_forward(self, visited=None):
        visited = visited or set()

        for task in self:
            if task.id in visited:
                continue

            visited.add(task.id)

            for dep in task.successor_dependency_ids:
                successor = dep.successor_task_id

                # Keep track of the old date to see if we actually need to keep moving forward
                old_start = successor.planned_start_date

                # Recalculate will safely assign the new date without triggering a rogue write loop
                # because we passed 'is_propagating=True' in the context
                successor._recalculate_schedule()

                # Only continue down the tree if this task's dates ACTUALLY changed
                if successor.planned_start_date != old_start:
                    successor._propagate_schedule_forward(visited)

    def _auto_link_subtask_dependencies(self):
        for task in self:
            # SCENARIO 1: Task relies on B -> Auto-add B's subtasks
            if task.depend_on_ids:
                # The 'child_of' operator brilliantly fetches the parent AND all nested subtasks
                all_deps_and_subtasks = self.env['project.task'].search([
                    ('id', 'child_of', task.depend_on_ids.ids)
                ])
                missing_deps = all_deps_and_subtasks - task.depend_on_ids - task

                if missing_deps:
                    # (4, ID) is the ORM command to link an existing record to a M2M field
                    task.write({
                        'depend_on_ids': [(4, dep.id) for dep in missing_deps]
                    })

            # SCENARIO 2: This task is a subtask of B -> Find tasks blocked by B, and block them with this task
            if task.parent_id:
                # Find any tasks that currently depend on this task's parent
                blocked_tasks = self.env['project.task'].search([
                    ('depend_on_ids', 'in', task.parent_id.id)
                ])

                for blocked in blocked_tasks:
                    if task not in blocked.depend_on_ids:
                        blocked.write({
                            'depend_on_ids': [(4, task.id)]
                        })

    # -----------------------------------------------------
    # Store actual purchase cost per task
    # -----------------------------------------------------
    @api.depends(
        'purchase_line_ids.price_subtotal', 'purchase_line_ids.state',
        'account_move_line_ids.balance', 'account_move_line_ids.move_id.state',
        'account_move_line_ids.purchase_line_id',
        'expense_ids.total_amount', 'expense_ids.state'
    )
    def _compute_actual_cost_total(self):
        for task in self:
            # 1. Aggregate Confirmed Purchase Orders Cost
            po_cost = sum(
                task.purchase_line_ids
                .filtered(lambda l: l.state in ('purchase', 'done'))
                .mapped('price_subtotal')
            )

            # 2. Aggregate Miscellaneous Journal Items / Standalone Vendor Bills
            # Filter out entries tied to PO lines or HR Expenses to avoid double-counting
            aml_cost = sum(
                task.account_move_line_ids
                .filtered(
                    lambda l: l.move_id.state == 'posted' and not l.purchase_line_id and not getattr(l, 'expense_id',
                                                                                                     False))
                .mapped('balance')  # 'balance' automatically uses company currency metrics (debit - credit)
            )

            # 3. Aggregate Approved/Done HR Expenses
            expense_cost = sum(
                task.expense_ids
                .filtered(lambda e: e.state in ('approved', 'done'))
                .mapped('total_amount')  # 'total_amount' is stored in Company Currency
            )

            task.actual_cost_total = po_cost + aml_cost + expense_cost

    @api.depends('actual_cost_total', 'child_ids.actual_cost_total_recursive')
    def _compute_actual_cost_total_recursive(self):
        for task in self:
            task.actual_cost_total_recursive = (
                    task.actual_cost_total
                    + sum(task.child_ids.mapped('actual_cost_total_recursive'))
            )

    @api.depends('estimated_cost_total', 'actual_cost_total_recursive')
    def _compute_cost_variance(self):
        for task in self:
            task.cost_variance = (
                    task.actual_cost_total_recursive - task.estimated_cost_total
            )


# -----------------------------------------------------
# Extend the project.milestone module to add a percent field as a weight and compute is_reached
# to reflect on the task's completion
# -----------------------------------------------------
class ProjectMilestone(models.Model):
    _inherit = 'project.milestone'

    is_reached = fields.Boolean(
        compute="_compute_is_reached",
        store=True,
        copy=False,
    )

    related_task_id = fields.Many2one(
        "project.task",
        string="Related Task",
        ondelete="set null",
        help="The primary task linked to this milestone."
    )

    contribution = fields.Integer(
        string="Contribution (%)",
        help="The contribution of this milestone to the overall progress.",
        readonly=True,
    )

    percent = fields.Float(
        string="Progress (%)",
        compute="_compute_percent",
        store=True,
        readonly=True,
        digits=(16, 2),
        help="Milestone completion (0.00–100.00). Automatically syncs with the related task's progress.",
    )

    overall_progress = fields.Float(
        string='Overall Progress (%)',
        compute='_compute_overall_progress',
        store=True,
        readonly=True,
    )

    @api.depends('related_task_id.progress_percent')
    def _compute_percent(self):
        for rec in self:
            if rec.related_task_id:
                # Directly map the floating precision value from the task
                rec.percent = rec.related_task_id.progress_percent
            else:
                # Preserve manual input or fallback smoothly to 0.0
                rec.percent = rec.percent or 0.0

    @api.onchange('percent')
    def _onchange_percent(self):
        for rec in self:
            if rec.percent > 100 or rec.percent < 0:
                rec.percent = min(max(rec.percent, 0), 100)
                return {
                    'warning': {
                        'title': _("Invalid Percentage"),
                        'message': _("Percentage must be between 0 and 100."),
                    }
                }

    @api.depends('contribution', 'percent')
    def _compute_overall_progress(self):
        for rec in self:
            rec.overall_progress = ((rec.contribution or 0) * (rec.percent or 0)) / 100.0

    @api.depends('percent')
    def _compute_is_reached(self):
        for m in self:
            m.is_reached = bool(m.percent == 100)


# -----------------------------------------------------
# Extend the project.project module with custom progress calculation
# -----------------------------------------------------
class ProjectProject(models.Model):
    _inherit = 'project.project'

    overall_progress = fields.Float(
        string='Overall Progress (%)',
        compute='_compute_overall_progress',
        store=True,
    )

    @api.depends('milestone_ids.percent', 'milestone_ids.related_task_id.progress_percent')
    def _compute_overall_progress(self):
        for project in self:
            total = 0.0
            for m in project.milestone_ids:
                total += m.overall_progress
            project.overall_progress = min(total, 100.0) / 100.0

    def unlink(self):
        """Intercepts project deletion to revert linked JCPs back to the priced state."""

        # 1. Identify linked JCPs before the project records are destroyed
        # We use self.ids to safely handle bulk deletions from the tree view
        linked_jcps = self.env['job.cost.project'].search([('project_id', 'in', self.ids)])

        # 2. Execute the standard Odoo deletion process
        result = super(ProjectProject, self).unlink()

        # 3. If deletion was successful, roll back the JCPs
        if result and linked_jcps:
            # Note: Odoo automatically sets project_id to False on the JCP
            # if your Many2one field uses the default ondelete='set null'.
            linked_jcps.write({'state': 'priced'})

            # Optional: Post a message to the JCP chatter for audit traceability
            for jcp in linked_jcps:
                jcp.message_post(
                    body="The associated operational project was deleted. The JCP has been reverted to the Priced state.")

        return result