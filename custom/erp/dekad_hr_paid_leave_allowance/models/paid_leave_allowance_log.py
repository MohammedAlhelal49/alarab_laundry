from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo import tools
from collections import defaultdict



class LeaveType(models.Model):
    _inherit = 'hr.leave.type'

    linked_to_paid_leave_allowance = fields.Boolean(string="Linked to Paid Leave Allowance")

    multiple_linked_leave_types = fields.Boolean(
        string="Multiple Linked Leave Types",
        compute="_compute_multiple_linked_leave_types",
        store=False
    )


    def get_allocation_data(self, employees, target_date=None):
        # Call the original method
        allocation_data = super().get_allocation_data(employees, target_date)

        # Loop through all employees
        for employee in employees:
            logs = self.env['paid.leave.allowance.log'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'approved'),
                ('leave_type_id', 'in', self.ids),
            ])
            if not logs:
                continue

            # Group logs by leave type
            log_data_by_type = defaultdict(float)
            for log in logs:
                log_data_by_type[log.leave_type_id.id] += log.days_requested

            # Inject log usage into allocation_data
            for i, leave_data in enumerate(allocation_data[employee]):
                leave_type_id = leave_data[3]
                if leave_type_id in log_data_by_type:
                    used_days = log_data_by_type[leave_type_id]

                    leave_data[1]['virtual_remaining_leaves'] -= used_days
                    leave_data[1]['remaining_leaves'] -= used_days
                    leave_data[1]['leaves_taken'] += used_days
                    leave_data[1]['virtual_leaves_taken'] += used_days
                    leave_data[1]['leaves_approved'] += used_days

                    # Optional: for better accuracy, you may also increase 'leaves_requested' if relevant
                    allocation_data[employee][i] = leave_data

        return allocation_data


    @api.depends('linked_to_paid_leave_allowance')
    def _compute_multiple_linked_leave_types(self):
        linked_leave_types = self.env['hr.leave.type'].search([
            ('linked_to_paid_leave_allowance', '=', True)
        ])
        self.multiple_linked_leave_types = len(linked_leave_types) > 1


class PaidLeaveAllowanceLog(models.Model):
    _name = 'paid.leave.allowance.log'
    _description = 'Paid Leave Allowance History'
    _order = 'request_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    user_id = fields.Many2one('res.users', string='Created By', readonly=True)
    remaining_before = fields.Float(string='Remaining Before', readonly=True)
    days_requested = fields.Float(string='Days Requested', readonly=True)
    remaining_after = fields.Float(string='Remaining After', readonly=True)
    request_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('refused', 'Refused')
    ], default='draft', string='Status', tracking=True)
    leave_id = fields.Many2one('hr.leave', string='Linked Leave Request', readonly=True)
    ae_total_salary = fields.Monetary(
        string="Total Salary",
        related="employee_id.contract_id.ae_total_salary",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="employee_id.contract_id.currency_id",
        store=True,
        readonly=True,
    )
    leave_allowance_amount = fields.Monetary(
        string="Leave Allowance Amount",
        compute="_compute_leave_allowance_amount",
        store=True,
        currency_field="currency_id",
    )
    leave_type_id = fields.Many2one(
        'hr.leave.type',
        string='Leave Type',
        required=True,
        domain="[('linked_to_paid_leave_allowance', '=', True)]"
    )

    @api.depends("ae_total_salary", "days_requested")
    def _compute_leave_allowance_amount(self):
        for record in self:
            daily_rate = (record.ae_total_salary or 0.0) / 30.0
            record.leave_allowance_amount = daily_rate * (record.days_requested or 0.0)

    def action_approve(self):
        for record in self:
            if record.state != 'draft':
                continue
            if record.days_requested <= 0:
                raise ValidationError(_("Requested days must be greater than zero."))
            record.remaining_after = record.remaining_before - record.days_requested
            record.state = 'approved'

    def action_refuse(self):
        for record in self:
            record.state = 'refused'

    def unlink(self):
        for record in self:
            if record.leave_id:
                raise ValidationError(_("You cannot delete a Paid Leave Allowance log that is linked to a leave request."))
        return super().unlink()


class LeaveReport(models.Model):
    _inherit = "hr.leave.employee.type.report"

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_leave_employee_type_report')

        self._cr.execute("""
            CREATE or REPLACE view hr_leave_employee_type_report AS (
                SELECT row_number() over(ORDER BY leaves.employee_id) as id,
                       leaves.employee_id as employee_id,
                       leaves.active_employee as active_employee,
                       leaves.number_of_days as number_of_days,
                       leaves.number_of_hours as number_of_hours,
                       leaves.department_id as department_id,
                       leaves.leave_type as leave_type,
                       leaves.holiday_status as holiday_status,
                       leaves.state as state,
                       leaves.date_from as date_from,
                       leaves.date_to as date_to,
                       leaves.company_id as company_id
                FROM (
                    SELECT
                        allocation.employee_id as employee_id,
                        employee.active as active_employee,
                        CASE
                            WHEN allocation.id = min_allocation_id.min_id
                                THEN aggregate_allocation.number_of_days - COALESCE(aggregate_leave.number_of_days, 0)
                                ELSE 0
                        END as number_of_days,
                        CASE
                            WHEN allocation.id = min_allocation_id.min_id
                                THEN aggregate_allocation.number_of_hours - COALESCE(aggregate_leave.number_of_hours, 0)
                                ELSE 0
                        END as number_of_hours,
                        allocation.department_id as department_id,
                        allocation.holiday_status_id as leave_type,
                        allocation.state as state,
                        allocation.date_from as date_from,
                        allocation.date_to as date_to,
                        'left' as holiday_status,
                        allocation.employee_company_id as company_id
                    FROM hr_leave_allocation as allocation
                    INNER JOIN hr_employee as employee ON allocation.employee_id = employee.id

                    LEFT JOIN (
                        SELECT employee_id, holiday_status_id, min(id) as min_id
                        FROM hr_leave_allocation
                        GROUP BY employee_id, holiday_status_id
                    ) min_allocation_id
                    ON allocation.employee_id = min_allocation_id.employee_id
                       AND allocation.holiday_status_id = min_allocation_id.holiday_status_id

                    LEFT JOIN (
                        SELECT employee_id, holiday_status_id,
                               sum(CASE WHEN state = 'validate' THEN number_of_days ELSE 0 END) as number_of_days,
                               sum(CASE WHEN state = 'validate' THEN number_of_hours_display ELSE 0 END) as number_of_hours
                        FROM hr_leave_allocation
                        GROUP BY employee_id, holiday_status_id
                    ) aggregate_allocation
                    ON allocation.employee_id = aggregate_allocation.employee_id
                       AND allocation.holiday_status_id = aggregate_allocation.holiday_status_id

                    LEFT JOIN (
                        SELECT employee_id, holiday_status_id,
                               SUM(number_of_days) AS number_of_days,
                               SUM(number_of_hours) AS number_of_hours
                        FROM (
                            SELECT
                                l.employee_id AS employee_id,
                                l.holiday_status_id AS holiday_status_id,
                                CASE WHEN l.state IN ('validate', 'validate1') THEN l.number_of_days ELSE 0 END AS number_of_days,
                                CASE WHEN l.state IN ('validate', 'validate1') THEN l.number_of_hours ELSE 0 END AS number_of_hours
                            FROM hr_leave l

                            UNION ALL

                            SELECT
                                pll.employee_id AS employee_id,
                                pll.leave_type_id AS holiday_status_id,
                                CASE WHEN pll.state = 'approved' THEN pll.days_requested ELSE 0 END AS number_of_days,
                                CASE WHEN pll.state = 'approved' THEN pll.days_requested * 8 ELSE 0 END AS number_of_hours
                            FROM paid_leave_allowance_log pll
                        ) combined
                        GROUP BY employee_id, holiday_status_id
                    ) aggregate_leave
                    ON allocation.employee_id = aggregate_leave.employee_id
                       AND allocation.holiday_status_id = aggregate_leave.holiday_status_id

                    UNION ALL

                    SELECT
                        request.employee_id as employee_id,
                        employee.active as active_employee,
                        request.number_of_days as number_of_days,
                        request.number_of_hours as number_of_hours,
                        request.department_id as department_id,
                        request.holiday_status_id as leave_type,
                        request.state as state,
                        request.date_from as date_from,
                        request.date_to as date_to,
                        CASE
                            WHEN request.state IN ('validate1', 'validate') THEN 'taken'
                            WHEN request.state = 'confirm' THEN 'planned'
                        END as holiday_status,
                        request.employee_company_id as company_id
                    FROM hr_leave as request
                    INNER JOIN hr_employee as employee ON request.employee_id = employee.id
                    WHERE request.state IN ('confirm', 'validate', 'validate1')

                    UNION ALL

                    SELECT
                        log.employee_id as employee_id,
                        emp.active as active_employee,
                        log.days_requested as number_of_days,
                        log.days_requested * 8 as number_of_hours,
                        emp.department_id as department_id,
                        log.leave_type_id as leave_type,
                        'validate' as state,
                        log.request_date as date_from,
                        log.request_date as date_to,
                        'taken' as holiday_status,
                        emp.company_id as company_id
                    FROM paid_leave_allowance_log log
                    INNER JOIN hr_employee emp ON log.employee_id = emp.id
                    INNER JOIN hr_leave_type pt ON pt.id = log.leave_type_id
                    WHERE log.state = 'approved'
                ) leaves
            );
        """)



class HrLeaveReport(models.Model):
    _inherit = "hr.leave.report"

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_leave_report')
        self._cr.execute("""
            CREATE OR REPLACE VIEW hr_leave_report AS (
                SELECT row_number() over(ORDER BY leaves.employee_id) as id,
                       leaves.leave_id as leave_id,
                       leaves.allocation_id as allocation_id,
                       leaves.employee_id as employee_id,
                       leaves.name as name,
                       leaves.number_of_days as number_of_days,
                       leaves.number_of_hours as number_of_hours,
                       leaves.leave_type as leave_type,
                       leaves.department_id as department_id,
                       leaves.holiday_status_id as holiday_status_id,
                       leaves.state as state,
                       leaves.date_from as date_from,
                       leaves.date_to as date_to,
                       leaves.company_id as company_id
                FROM (
                    SELECT
                        allocation.id as allocation_id,
                        NULL as leave_id,
                        allocation.employee_id as employee_id,
                        allocation.name as name,
                        allocation.number_of_days as number_of_days,
                        allocation.number_of_hours_display as number_of_hours,
                        'allocation' as leave_type,
                        allocation.department_id as department_id,
                        allocation.holiday_status_id as holiday_status_id,
                        allocation.state as state,
                        allocation.date_from as date_from,
                        allocation.date_to as date_to,
                        allocation.employee_company_id as company_id
                    FROM hr_leave_allocation as allocation
                    INNER JOIN hr_employee as employee ON allocation.employee_id = employee.id
                    WHERE employee.active IS TRUE

                    UNION ALL

                    SELECT
                        request.id as leave_id,
                        NULL as allocation_id,
                        request.employee_id as employee_id,
                        request.private_name as name,
                        (request.number_of_days * -1) as number_of_days,
                        (request.number_of_hours * -1) as number_of_hours,
                        'request' as leave_type,
                        request.department_id as department_id,
                        request.holiday_status_id as holiday_status_id,
                        request.state as state,
                        request.date_from as date_from,
                        request.date_to as date_to,
                        request.employee_company_id as company_id
                    FROM hr_leave as request
                    INNER JOIN hr_employee as employee ON request.employee_id = employee.id
                    WHERE employee.active IS TRUE

                    UNION ALL

                    SELECT
                        NULL as leave_id,
                        NULL as allocation_id,
                        log.employee_id as employee_id,
                        log.name as name,
                        (log.days_requested * -1) as number_of_days,
                        (log.days_requested * 8 * -1) as number_of_hours,
                        'request' as leave_type,
                        emp.department_id as department_id,
                        log.leave_type_id as holiday_status_id,
                        'validate' as state,
                        log.request_date as date_from,
                        log.request_date as date_to,
                        emp.company_id as company_id
                    FROM paid_leave_allowance_log log
                    INNER JOIN hr_employee emp ON log.employee_id = emp.id
                    WHERE log.state = 'approved'
                ) leaves
            );
        """)




