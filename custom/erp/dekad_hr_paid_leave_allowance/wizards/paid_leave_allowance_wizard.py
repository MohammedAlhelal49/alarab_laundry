from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PaidLeaveAllowanceWizard(models.TransientModel):
    _name = 'paid.leave.allowance.wizard'
    _description = 'Paid Leave Allowance Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    days_requested = fields.Float(string='Days Requested', required=True)

    remaining_days = fields.Float(
        string='Remaining Paid Days', compute='_compute_remaining_days'
    )

    @api.depends('employee_id', 'days_requested')
    def _compute_remaining_days(self):
        for wizard in self:
            wizard.remaining_days = 0.0
            if not wizard.employee_id:
                continue

            leave_types = self.env['hr.leave.type'].sudo().search([
                ('linked_to_paid_leave_allowance', '=', True),
                ('requires_allocation', '=', 'yes'),
            ])

            if not leave_types:
                continue

            total_remaining = 0.0

            for paid_type in leave_types:
                data = paid_type.sudo().get_allocation_data(wizard.employee_id)
                employee_data = data.get(wizard.employee_id)

                if employee_data:
                    for item in employee_data:
                        virtual_remaining = item[1].get('virtual_remaining_leaves', 0.0)
                        total_remaining += virtual_remaining

            wizard.remaining_days = total_remaining


    def action_submit(self):
        self.ensure_one()

        # ✅ Check for existing draft requests
        existing_draft = self.env['paid.leave.allowance.log'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'draft')
        ], limit=1)

        if existing_draft:
            raise ValidationError(_(
                "This employee already has a pending Paid Leave Allowance request in draft state."
            ))

        # ✅ Ensure requested days > 0
        if self.days_requested <= 0:
            raise ValidationError(_("Requested days must be greater than zero."))

        if self.remaining_days <= 0:
            raise ValidationError(_("This employee has no remaining Paid Time Off days."))

        if self.days_requested > self.remaining_days:
            raise ValidationError(_("Requested days exceed remaining paid leave days."))

        # Find the leave type linked to Paid Leave Allowance
        paid_type = self.env['hr.leave.type'].sudo().search([
            ('linked_to_paid_leave_allowance', '=', True),
            ('requires_allocation', '=', 'yes'),
        ], limit=1)

        if not paid_type:
            raise ValidationError(_("No leave type is linked to Paid Leave Allowance."))

        remaining_after = self.remaining_days - self.days_requested

        self.env['paid.leave.allowance.log'].create({
            'name': _("Paid Leave Allowance - %s", fields.Date.today()),
            'employee_id': self.employee_id.id,
            'user_id': self.env.user.id,
            'days_requested': self.days_requested,
            'remaining_before': self.remaining_days,
            'remaining_after': remaining_after,
            'leave_type_id': paid_type.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Paid Leave Logs',
            'res_model': 'paid.leave.allowance.log',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('employee_id', '=', self.employee_id.id)],
        }
