from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DePeriod(models.Model):
    _name = 'de.period'
    _description = 'School Day Period'
    _order = 'start_time'

    name = fields.Char(string='Label', required=True, help="e.g., Period 1")
    start_time = fields.Float(string='Start Time', required=True, help='Enter time in decimal format (e.g., 8.5 = 08:30, 11.75 = 11:45)')
    end_time = fields.Float(string='End Time', required=True)
    duration = fields.Float(string='Duration (mins)', compute='_compute_duration', store=True , help='Use decimal format: .25 = 15 min, .5 = 30 min, .75 = 45 min')
    #edit by ahmad 30/9
    is_break = fields.Boolean(string='Is Break/Lunch', default=False,
                              help='Check this if this period is a break, lunch, or non-teaching time')
    active = fields.Boolean(default=True)


    _sql_constraints = [
        ('period_time_unique', 'unique(start_time, end_time)', 'A period with the same start and end time already exists!')
    ]

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if rec.start_time and rec.end_time and rec.end_time > rec.start_time:
                rec.duration = (rec.end_time - rec.start_time) * 60
            else:
                rec.duration = 0.0

    @api.constrains('start_time', 'end_time')
    def _check_time_validity(self):
        for rec in self:
            if rec.start_time and rec.end_time and rec.start_time >= rec.end_time:
                raise ValidationError(_('Start time must be before end time.'))
