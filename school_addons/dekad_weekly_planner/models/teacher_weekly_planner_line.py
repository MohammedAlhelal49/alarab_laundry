# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class TeacherWeeklyPlannerLine(models.Model):
    """
    Line model for individual time slots in the weekly planner.
    Each line represents one activity/time slot for a specific day.
    """
    _name = 'teacher.weekly.planner.line'
    _description = 'Teacher Weekly Planner Line'
    _order = 'planner_id, day_of_week_order, start_time'
    _rec_name = 'display_name'

    # Parent Relation
    planner_id = fields.Many2one(
        'teacher.weekly.planner',
        string='Weekly Planner',
        required=True,
        ondelete='cascade',
        index=True
    )

    teacher_id = fields.Many2one(
        related='planner_id.teacher_id',
        string='Teacher',
        store=True,
        readonly=True
    )

    state = fields.Selection(
        related='planner_id.state',
        string='Planner Status',
        store=True,
        readonly=True
    )

    # Day Selection
    day_of_week = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday')
    ], string='Day of Week', required=True, index=True)

    day_of_week_order = fields.Integer(
        string='Day Order',
        compute='_compute_day_of_week_order',
        store=True
    )

    # Time Fields
    start_time = fields.Float(
        string='Start Time',
        required=True,
        help='Start time in 24-hour format (e.g., 8.5 for 8:30 AM)'
    )

    end_time = fields.Float(
        string='End Time',
        required=True,
        help='End time in 24-hour format (e.g., 17.5 for 5:30 PM)'
    )

    duration = fields.Float(
        string='Duration (Hours)',
        compute='_compute_duration',
        store=True,
        readonly=True
    )

    start_time_formatted = fields.Char(
        string='Start',
        compute='_compute_formatted_times',
        store=True
    )

    end_time_formatted = fields.Char(
        string='End',
        compute='_compute_formatted_times',
        store=True
    )

    # Activity Details
    activity_type = fields.Selection([
        ('lesson', 'Lesson'),
        ('preparation', 'Preparation'),
        ('meeting', 'Meeting'),
        ('other', 'Other')
    ], string='Activity Type', required=True, default='lesson')

    subject_id = fields.Many2one(
        'de.subject',
        string='Subject',
        ondelete='restrict'
    )

    classroom_id = fields.Many2one(
        'de.classroom',
        string='Classroom',
        ondelete='restrict'
    )

    grade_id = fields.Many2one(
        related='classroom_id.grade_id',
        string='Grade',
        store=True,
        readonly=True
    )

    notes = fields.Text(string='Notes')

    # Display
    display_name = fields.Char(
        string='Description',
        compute='_compute_display_name',
        store=True
    )

    # Color for calendar view
    color = fields.Integer(string='Color', default=0)

    @api.depends('day_of_week')
    def _compute_day_of_week_order(self):
        """Compute numeric order for days to enable proper sorting"""
        day_order = {
            'monday': 1,
            'tuesday': 2,
            'wednesday': 3,
            'thursday': 4,
            'friday': 5,
            'saturday': 6,
            'sunday': 7
        }
        for record in self:
            record.day_of_week_order = day_order.get(record.day_of_week, 0)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        """Calculate duration in hours"""
        for record in self:
            if record.start_time and record.end_time:
                record.duration = record.end_time - record.start_time
            else:
                record.duration = 0.0

    @api.depends('start_time', 'end_time')
    def _compute_formatted_times(self):
        """Format time floats to HH:MM format"""
        for record in self:
            record.start_time_formatted = self._float_to_time_string(record.start_time)
            record.end_time_formatted = self._float_to_time_string(record.end_time)

    def _float_to_time_string(self, time_float):
        """Convert float time to string format (e.g., 8.5 -> '08:30')"""
        if not time_float:
            return '00:00'
        hours = int(time_float)
        minutes = int((time_float - hours) * 60)
        return f'{hours:02d}:{minutes:02d}'

    @api.depends('day_of_week', 'start_time', 'end_time', 'activity_type', 'subject_id', 'classroom_id')
    def _compute_display_name(self):
        """Generate descriptive display name"""
        for record in self:
            parts = []

            # Day
            if record.day_of_week:
                parts.append(dict(record._fields['day_of_week'].selection).get(record.day_of_week))

            # Time
            if record.start_time and record.end_time:
                parts.append(f"{record.start_time_formatted}-{record.end_time_formatted}")

            # Activity
            if record.activity_type:
                parts.append(dict(record._fields['activity_type'].selection).get(record.activity_type))

            # Subject
            if record.subject_id:
                parts.append(record.subject_id.name)

            # Classroom
            if record.classroom_id:
                parts.append(f"({record.classroom_id.name})")

            record.display_name = ' - '.join(parts) if parts else _('New Activity')

    @api.constrains('start_time', 'end_time')
    def _check_time_validity(self):
        """Validate time ranges"""
        for record in self:
            # Check valid time range (0-24)
            if not (0 <= record.start_time < 24):
                raise ValidationError(_('Start time must be between 0:00 and 23:59!'))
            if not (0 <= record.end_time <= 24):
                raise ValidationError(_('End time must be between 0:00 and 24:00!'))

            # Check start < end
            if record.start_time >= record.end_time:
                raise ValidationError(_('Start time must be before end time!'))

            # Check reasonable duration (max 8 hours for a single slot)
            if record.duration > 8:
                raise ValidationError(_('A single time slot cannot exceed 8 hours!'))

    @api.constrains('planner_id', 'day_of_week', 'start_time', 'end_time')
    def _check_overlapping_slots(self):
        """
        Prevent overlapping time slots for the same teacher on the same day.
        This ensures no scheduling conflicts.
        """
        for record in self:
            # Search for overlapping slots
            domain = [
                ('planner_id', '=', record.planner_id.id),
                ('day_of_week', '=', record.day_of_week),
                ('id', '!=', record.id),
            ]

            overlapping = self.search(domain)

            for slot in overlapping:
                # Check if time ranges overlap
                # Overlap occurs if: start_time < other.end_time AND end_time > other.start_time
                if record.start_time < slot.end_time and record.end_time > slot.start_time:
                    raise ValidationError(
                        _('Time slot overlaps with another activity on %s:\n'
                          'Existing: %s - %s\n'
                          'New: %s - %s') % (
                            dict(record._fields['day_of_week'].selection).get(record.day_of_week),
                            slot.start_time_formatted,
                            slot.end_time_formatted,
                            record.start_time_formatted,
                            record.end_time_formatted
                        )
                    )

    @api.onchange('activity_type')
    def _onchange_activity_type(self):
        """Clear subject/classroom if not lesson type"""
        if self.activity_type != 'lesson':
            self.subject_id = False
            self.classroom_id = False

    @api.onchange('classroom_id')
    def _onchange_classroom_id(self):
        """Filter subjects based on classroom's grade"""
        if self.classroom_id and self.classroom_id.grade_id:
            return {
                'domain': {
                    'subject_id': [('grade_id', '=', self.classroom_id.grade_id.id)]
                }
            }
        else:
            return {'domain': {'subject_id': []}}

    def name_get(self):
        """Custom name_get for better readability"""
        result = []
        for record in self:
            name = record.display_name
            result.append((record.id, name))
        return result
