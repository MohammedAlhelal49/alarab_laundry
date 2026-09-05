from odoo import models, fields, api


class AccountMoveProjectReportWizard(models.TransientModel):
    _name = 'account.move.project.report.wizard'
    _description = 'Account Move Project Report Wizard'

    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners'
    )

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True
    )

    account_ids = fields.Many2many(
        'account.account',
        string='Accounts'
    )

    task_ids = fields.Many2many(
        'project.task',
        string='Project Tasks',
        domain="[('project_id', '=', project_id)]"
    )

    journal_ids = fields.Many2many(
        'account.journal',
        string='Journals'
    )

    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")

    currency_id = fields.Many2one('res.currency', string='Target Currency', required=True,
                                  default=lambda self: self.env.company.currency_id)

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            self.task_ids = self.task_ids.filtered(
                lambda t: t.project_id == self.project_id
            )
        else:
            self.task_ids = [(5, 0, 0)]

    def action_preview(self):
        self.ensure_one()

        # 1. Clear previous results for this user
        self.env['account.move.line.report'].search([
            ('create_uid', '=', self.env.user.id)
        ]).unlink()

        # 2. Build the domain to find the SOURCE data
        domain = [('move_id.state', '=', 'posted')]
        if self.project_id:
            domain.append(('move_id.project_id', '=', self.project_id.id))
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        # --- TASK & SUBTASK FILTERING ---
        if self.task_ids:
            # Fetches the selected tasks AND any subtasks where parent_id is in self.task_ids
            all_task_ids = self.env['project.task'].search([
                ('id', 'child_of', self.task_ids.ids)
            ]).ids
            domain.append(('task_id', 'in', all_task_ids))

        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))

        source_lines = self.env['account.move.line'].search(domain)

        # Grab the target currency selected in the wizard
        target_currency = self.currency_id

        # 3. Create the REPORT records with Conversion
        report_values = []
        for line in source_lines:
            company_currency = line.company_id.currency_id
            transaction_date = line.date or fields.Date.context_today(self)

            converted_debit = company_currency._convert(line.debit, target_currency, line.company_id, transaction_date)
            converted_credit = company_currency._convert(line.credit, target_currency, line.company_id,
                                                         transaction_date)
            converted_balance = company_currency._convert(line.balance, target_currency, line.company_id,
                                                          transaction_date)

            report_values.append({
                'move_id': line.move_id.id,
                'move_name': line.move_id.name,
                'date': line.date,
                'journal_id': line.journal_id.id,
                'account_id': line.account_id.id,
                'partner_id': line.partner_id.id,
                'project_id': line.move_id.project_id.id,
                'task_id': line.task_id.id,
                'company_currency_id': target_currency.id,
                'debit': converted_debit,
                'credit': converted_credit,
                'balance': converted_balance,
            })

        if report_values:
            self.env['account.move.line.report'].create(report_values)

        return {
            'type': 'ir.actions.act_window',
            'name': f"Report: {self.project_id.name} ({target_currency.name})",
            'res_model': 'account.move.line.report',
            'view_mode': 'list,pivot,graph',
            'domain': [('create_uid', '=', self.env.user.id)],
            'target': 'current',
        }
