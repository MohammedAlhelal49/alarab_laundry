from odoo import models, fields


class AccountMoveLineReport(models.TransientModel):
    _name = 'account.move.line.report'
    _description = 'Journal Items Reporting'

    # Core move info
    move_id = fields.Many2one('account.move')
    move_name = fields.Char()
    move_type = fields.Selection(selection=[])
    ref = fields.Char()

    journal_id = fields.Many2one('account.journal')
    company_id = fields.Many2one('res.company')
    company_currency_id = fields.Many2one('res.currency')
    date = fields.Date()

    # Accounting dimensions
    account_id = fields.Many2one('account.account')
    partner_id = fields.Many2one('res.partner')
    # analytic_account_id = fields.Many2one('account.analytic.account')

    # Project tracking
    project_id = fields.Many2one('project.project')
    task_id = fields.Many2one('project.task')

    # Taxes
    tax_line_id = fields.Many2one('account.tax')

    # Multi-currency support
    currency_id = fields.Many2one('res.currency')

    amount_currency = fields.Monetary(currency_field='currency_id', group_operator='sum')

    # Aggregated amounts (company currency)
    debit = fields.Monetary(currency_field='company_currency_id', group_operator='sum')
    credit = fields.Monetary(currency_field='company_currency_id', group_operator='sum')
    balance = fields.Monetary(currency_field='company_currency_id', group_operator='sum')
