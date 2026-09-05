from odoo import models, fields, api


class DeTimetableLine(models.Model):
    _name = 'de.timetable.line'
    _description = 'Timetable Line'

    timetable_id = fields.Many2one('de.timetable', string='Timetable', required=True, ondelete='cascade')
    session_slot_id = fields.Many2one('de.session.slot', string='Session Slot', required=True, ondelete='restrict')
    subject_id = fields.Many2one('de.subject', string='Subject')  # Not required - for breaks
    teacher_id = fields.Many2one('de.teacher', string='Teacher')  # Not required - for breaks
    # Related fields for display
    day_of_week = fields.Selection(string='Day', related='session_slot_id.day_of_week', readonly=True, store=True)
    period_id = fields.Many2one('de.period', string='Period', related='session_slot_id.period_id', store=True,
                                readonly=True)
    period_name = fields.Char(string='Period Name', related='period_id.name', readonly=True)
    period_start_time = fields.Float(string='Start Time', related='period_id.start_time', readonly=True)
    period_end_time = fields.Float(string='End Time', related='period_id.end_time', readonly=True)

    # edit by ahmad 30/9 ,computed field to check if this is a break period
    is_break = fields.Boolean(string='Is Break', related='session_slot_id.period_id.is_break', store=True)

    _sql_constraints = [
        ('unique_timetable_slot',
         'unique(timetable_id, session_slot_id)',
         'This time slot is already assigned in this timetable!')
    ]

    @api.onchange('session_slot_id')
    def _onchange_session_slot_id(self):
        """Clear subject and teacher if it's a break period"""
        if self.session_slot_id and self.session_slot_id.period_id.is_break:
            self.subject_id = False
            self.teacher_id = False