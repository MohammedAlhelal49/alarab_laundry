from datetime import timedelta
from odoo import models, fields


class ActivityLoggerKPIWizard(models.TransientModel):
    _name = 'activity.logger.kpi.wizard'
    _description = 'Activity KPI Wizard'

    user_id = fields.Many2one(
        'res.users',
        required=True,
        string='User'
    )

    date_from = fields.Datetime(
        string='Date'
    )

    date_to = fields.Datetime(
        string='To Date'
    )

    def action_show_report(self):
        self.ensure_one()

        self.env['activity.logger.kpi'].search([]).unlink()

        base_domain = [
            ('user_id', '=', self.user_id.id),
            ('log_source', '!=', 'system'),
        ]

        if self.date_from:
            base_domain.append(
                ('create_date', '>=', self.date_from)
            )

        if self.date_to:
            base_domain.append(
                ('create_date', '<=', self.date_to)
            )

        logs = self.env['activity.logger'].search(
            base_domain,
            order='create_date'
        )

        if not logs:
            return {
                'type': 'ir.actions.act_window',
                'name': f'User KPI Report - ({self.user_id.name})',
                'res_model': 'activity.logger.kpi',
                'view_mode': 'list',
                'target': 'current',
            }

        dates = sorted(
            set(
                logs.mapped(
                    lambda l: l.create_date.date()
                )
            )
        )

        for current_date in dates:

            day_logs = logs.filtered(
                lambda l:
                l.create_date
                and l.create_date.date() == current_date
            )

            create_count = len(
                day_logs.filtered(
                    lambda l: l.operation_type == 'create'
                )
            )

            write_count = len(
                day_logs.filtered(
                    lambda l: l.operation_type == 'write'
                )
            )

            delete_count = len(
                day_logs.filtered(
                    lambda l: l.operation_type == 'unlink'
                )
            )

            first_activity = False
            last_activity = False
            working_hours = '0:00'

            if day_logs:

                activity_dates = day_logs.mapped(
                    'create_date'
                )

                first_activity = min(
                    activity_dates
                )

                last_activity = max(
                    activity_dates
                )

                duration = (
                    last_activity -
                    first_activity
                )

                total_seconds = int(
                    duration.total_seconds()
                )

                hours = total_seconds // 3600

                minutes = (
                    total_seconds % 3600
                ) // 60

                working_hours = (
                    f"{hours}:{minutes:02d}"
                )

            self.env['activity.logger.kpi'].create({
                'date': current_date,
                'user_id': self.user_id.id,
                'create_count': create_count,
                'write_count': write_count,
                'delete_count': delete_count,
                'total_transactions':
                    create_count +
                    write_count +
                    delete_count,
                'first_activity': first_activity,
                'last_activity': last_activity,
                'working_hours': working_hours,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': f'User KPI Report - ({self.user_id.name})',
            'res_model': 'activity.logger.kpi',
            'view_mode': 'list',
            'target': 'current',
        }