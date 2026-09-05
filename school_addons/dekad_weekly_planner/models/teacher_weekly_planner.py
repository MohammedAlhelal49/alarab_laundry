# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta


class TeacherWeeklyPlanner(models.Model):
    """
    Main model for managing teacher weekly schedules.
    Teachers can plan their activities across the week including lessons,
    preparation time, meetings, and other activities.
    """
    _name = 'teacher.weekly.planner'
    _description = 'Teacher Weekly Planner'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'week_start_date desc, teacher_id'
    _rec_name = 'display_name'

    # Basic Information
    name = fields.Char(
        string='Planner Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )

    teacher_id = fields.Many2one(
        'de.teacher',
        string='Teacher',
        required=True,
        tracking=True,
        ondelete='cascade',
        index=True
    )

    teacher_name = fields.Char(
        related='teacher_id.name',
        string='Teacher Name',
        store=True,
        readonly=True
    )

    # Week Dates
    week_start_date = fields.Date(
        string='Week Start Date',
        required=True,
        tracking=True,
        default=fields.Date.context_today
    )

    week_end_date = fields.Date(
        string='Week End Date',
        compute='_compute_week_end_date',
        store=True,
        readonly=True
    )

    week_number = fields.Integer(
        string='Week Number',
        compute='_compute_week_number',
        store=True,
        readonly=True
    )

    # Lines
    line_ids = fields.One2many(
        'teacher.weekly.planner.line',
        'planner_id',
        string='Planning Lines',
        copy=True
    )

    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, copy=False)

    # Computed Statistics
    total_hours = fields.Float(
        string='Total Hours',
        compute='_compute_total_hours',
        store=True,
        readonly=True
    )

    lesson_hours = fields.Float(
        string='Teaching Hours',
        compute='_compute_lesson_hours',
        store=True,
        readonly=True
    )

    line_count = fields.Integer(
        string='Activities Count',
        compute='_compute_line_count',
        store=True,
        readonly=True
    )

    # Additional Info
    notes = fields.Text(string='Notes')

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    active = fields.Boolean(default=True)

    # SQL Constraints
    _sql_constraints = [
        ('unique_teacher_week',
         'UNIQUE(teacher_id, week_start_date)',
         'A teacher can only have one planner per week!')
    ]

    @api.model
    def create(self, vals):
        """Override create to generate sequence number"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('teacher.weekly.planner') or _('New')
        return super(TeacherWeeklyPlanner, self).create(vals)

    @api.depends('week_start_date')
    def _compute_week_end_date(self):
        """Compute week end date as 6 days after start date"""
        for record in self:
            if record.week_start_date:
                record.week_end_date = record.week_start_date + timedelta(days=6)
            else:
                record.week_end_date = False

    @api.depends('week_start_date')
    def _compute_week_number(self):
        """Compute ISO week number"""
        for record in self:
            if record.week_start_date:
                record.week_number = record.week_start_date.isocalendar()[1]
            else:
                record.week_number = 0

    @api.depends('teacher_id', 'week_start_date', 'name')
    def _compute_display_name(self):
        """Compute display name for better identification"""
        for record in self:
            if record.teacher_id and record.week_start_date:
                record.display_name = f"{record.teacher_id.name} - Week {record.week_number} ({record.week_start_date})"
            else:
                record.display_name = record.name or _('New')

    @api.depends('line_ids', 'line_ids.duration')
    def _compute_total_hours(self):
        """Calculate total hours across all activities"""
        for record in self:
            record.total_hours = sum(record.line_ids.mapped('duration'))

    @api.depends('line_ids', 'line_ids.duration', 'line_ids.activity_type')
    def _compute_lesson_hours(self):
        """Calculate total teaching hours (lesson type only)"""
        for record in self:
            lesson_lines = record.line_ids.filtered(lambda l: l.activity_type == 'lesson')
            record.lesson_hours = sum(lesson_lines.mapped('duration'))

    @api.depends('line_ids')
    def _compute_line_count(self):
        """Count number of planning lines"""
        for record in self:
            record.line_count = len(record.line_ids)

    @api.constrains('week_start_date')
    def _check_week_start_date(self):
        """Validate that week start date is Monday"""
        for record in self:
            if record.week_start_date and record.week_start_date.weekday() != 0:
                raise ValidationError(_('Week start date must be a Monday!'))

    def action_generate_default_week(self):
        """
        Generate default weekly template with Monday to Friday slots.
        Creates morning and afternoon sessions for each weekday.
        """
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(_('You can only generate template for draft planners!'))

        # Clear existing lines
        self.line_ids.unlink()

        # Days to generate (Monday to Friday)
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']

        # Default time slots
        time_slots = [
            {'start': 8.0, 'end': 10.0, 'activity': 'lesson'},
            {'start': 10.0, 'end': 12.0, 'activity': 'lesson'},
            {'start': 13.0, 'end': 15.0, 'activity': 'lesson'},
            {'start': 15.0, 'end': 17.0, 'activity': 'preparation'},
        ]

        lines_to_create = []
        for day in days:
            for slot in time_slots:
                lines_to_create.append({
                    'planner_id': self.id,
                    'day_of_week': day,
                    'start_time': slot['start'],
                    'end_time': slot['end'],
                    'activity_type': slot['activity'],
                    'notes': _('Auto-generated slot')
                })

        self.env['teacher.weekly.planner.line'].create(lines_to_create)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Default weekly template generated successfully!'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_confirm(self):
        """Confirm the weekly planner"""
        for record in self:
            if not record.line_ids:
                raise UserError(_('Cannot confirm an empty planner! Please add at least one activity.'))
            record.state = 'confirmed'

    def action_draft(self):
        """Set planner back to draft"""
        self.write({'state': 'draft'})

    def action_cancel(self):
        """Cancel the weekly planner"""
        self.write({'state': 'cancelled'})

    def action_view_lines(self):
        """Open list view of planning lines"""
        self.ensure_one()
        return {
            'name': _('Planning Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'teacher.weekly.planner.line',
            'view_mode': 'list,form',
            'domain': [('planner_id', '=', self.id)],
            'context': {'default_planner_id': self.id},
            'target': 'current',
        }

    def action_print_weekly_schedule(self):
        """Print weekly timetable report"""
        self.ensure_one()
        return self.env.ref('dekad_weekly_planner.action_report_weekly_planner').report_action(self)

    def name_get(self):
        """Custom name_get to show meaningful names"""
        result = []
        for record in self:
            name = record.display_name or record.name
            result.append((record.id, name))
        return result
