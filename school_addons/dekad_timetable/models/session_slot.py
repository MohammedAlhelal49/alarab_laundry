from odoo import models, fields, api

class DeSessionSlot(models.Model):
    _name = 'de.session.slot'
    _description = 'Session Slot'
    _order = 'day_of_week, period_id'

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    day_of_week = fields.Selection([
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ], string='Day of Week', required=True)
    period_id = fields.Many2one('de.period', string='Period', required=True, ondelete="cascade")
    # Related fields from period
    period_start_time = fields.Float(string='Start Time', related='period_id.start_time', readonly=True)
    period_end_time = fields.Float(string='End Time', related='period_id.end_time', readonly=True)
    period_duration = fields.Float(string='Duration', related='period_id.duration', readonly=True)
    is_break = fields.Boolean(string='Is Break', related='period_id.is_break', readonly=True)

    _sql_constraints = [
        ('unique_day_period', 'unique(day_of_week, period_id)', 'This day and period combination already exists!')
    ]

    @api.depends('day_of_week', 'period_id.name')
    def _compute_name(self):
        for rec in self:
            if rec.day_of_week and rec.period_id:
                day_name = dict(self._fields['day_of_week'].selection).get(rec.day_of_week)
                rec.name = f"{day_name} - {rec.period_id.name}"
            else:
                rec.name = '/'
