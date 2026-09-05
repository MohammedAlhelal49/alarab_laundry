from odoo import models, fields


class ActivityLoggerKPI(models.TransientModel):
    _name = 'activity.logger.kpi'
    _description = 'Activity Logger KPI'

    date = fields.Datetime(
        readonly=True
    )

    user_id = fields.Many2one(
        'res.users',
        readonly=True
    )

    create_count = fields.Integer(
        string='Created Transactions',
        readonly=True
    )

    write_count = fields.Integer(
        string='Updated Transactions',
        readonly=True
    )

    delete_count = fields.Integer(
        string='Deleted Transactions',
        readonly=True
    )

    total_transactions = fields.Integer(
        string='Total Transactions',
        readonly=True
    )

    first_activity = fields.Datetime(
        string='First Activity',
        readonly=True
    )

    last_activity = fields.Datetime(
        string='Last Activity',
        readonly=True
    )

    working_hours = fields.Char(
        string='Active Duration'
    )