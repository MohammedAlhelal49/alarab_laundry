# -*- coding: utf-8 -*-
from odoo import models


class AccountGeneralLedgerProjectFilter(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(
            report, options, previous_options=previous_options
        )
        prev = previous_options or {}

        options['filter_project_id'] = prev.get('filter_project_id', False)

        # Reset task selection when project changes to avoid stale ids
        prev_project = prev.get('filter_project_id', False)
        curr_project = options['filter_project_id']
        if curr_project and curr_project == prev_project:
            options['filter_task_ids'] = prev.get('filter_task_ids', [])
        else:
            options['filter_task_ids'] = []


class AccountReportProjectDomain(models.Model):
    _inherit = 'account.report'

    def _get_options_domain(self, options, date_scope):
        domain = super()._get_options_domain(options, date_scope)

        # Guard: only apply when keys are present (GL only — injected by
        # AccountGeneralLedgerProjectFilter._custom_options_initializer).
        # Other reports never have these keys so this block is never reached.
        if options.get('filter_project_id'):
            domain.append(
                ('move_id.project_id', '=', options['filter_project_id'])
            )

        # task_ids meaningful only when project is also set
        if options.get('filter_project_id') and options.get('filter_task_ids'):
            domain.append(
                ('task_id', 'in', options['filter_task_ids'])
            )

        return domain
