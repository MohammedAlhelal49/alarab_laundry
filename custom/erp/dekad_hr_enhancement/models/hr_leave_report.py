# -*- coding: utf-8 -*-
from odoo import api, models


class LeaveReportInherit(models.Model):
    _inherit = "hr.leave.employee.type.report"

    @api.model
    def action_time_off_analysis(self):
        action = super().action_time_off_analysis()
        list_view = self.env.ref(
            'dekad_hr_enhancement.hr_leave_employee_type_report_view_list',
            raise_if_not_found=False
        )
        pivot_view = self.env.ref(
            'hr_holidays.hr_leave_employee_type_report',
            raise_if_not_found=False
        )

        views = []
        if list_view:
            views.append((list_view.id, 'list'))
        if pivot_view:
            views.append((pivot_view.id, 'pivot'))

        if views:
            action['views'] = views
            action['view_mode'] = ','.join(v[1] for v in views)

        return action