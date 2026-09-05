from odoo import models, fields, api, _
from odoo.exceptions import UserError
import random


class GenerateTimetableWizard(models.TransientModel):
    _name = 'generate.timetable.wizard'
    _description = 'Generate Timetable Wizard'

    academic_year_id = fields.Many2one('de.academic.year', required=True)
    academic_term_id = fields.Many2one('de.academic.term', required=True)
    grade_id = fields.Many2one('de.grade', required=True)
    classroom_id = fields.Many2one('de.classroom', required=True)
    periods_per_day = fields.Integer(string="Periods per Day", default=5, required=True)

    def action_generate(self):
        Timetable = self.env['de.timetable']
        SessionSlot = self.env['de.session.slot']
        TimetableLine = self.env['de.timetable.line']

        # Check if timetable already exists
        existing = Timetable.search([
            ('academic_term_id', '=', self.academic_term_id.id),
            ('classroom_id', '=', self.classroom_id.id)
        ])
        if existing:
            raise UserError(_('A timetable already exists for this classroom and term.'))

        # Create the new timetable
        timetable = Timetable.create({
            'name': f"{self.grade_id.name or ''} - {self.classroom_id.name or ''} - {self.academic_term_id.name or ''}",
            'academic_year_id': self.academic_year_id.id,
            'academic_term_id': self.academic_term_id.id,
            'grade_id': self.grade_id.id,
            'classroom_id': self.classroom_id.id,
        })

        # Get all session slots
        all_slots = SessionSlot.search([], order="day_of_week, period_id")

        # Separate teaching slots from break slots
        teaching_slots = all_slots.filtered(lambda s: not s.period_id.is_break)
        break_slots = all_slots.filtered(lambda s: s.period_id.is_break)

        subjects = self.grade_id.subject_ids
        if not subjects:
            raise UserError(_('No subjects found for the selected grade.'))

        subjects_per_day = {}

        # Process teaching slots only
        for slot in teaching_slots:
            if not slot or not slot.id:
                continue

            day = slot.day_of_week
            if day not in subjects_per_day or not subjects_per_day[day]:
                subjects_per_day[day] = random.sample(list(subjects), len(subjects))

            subject = subjects_per_day[day].pop()
            if not subject:
                continue
            teacher = subject.teacher_ids[0] if subject.teacher_ids else None

            if not teacher:
                continue

            TimetableLine.create({
                'timetable_id': timetable.id,
                'session_slot_id': slot.id,
                'subject_id': subject.id,
                'teacher_id': teacher.id,
            })

        # Create break entries without subject/teacher
        for slot in break_slots:
            TimetableLine.create({
                'timetable_id': timetable.id,
                'session_slot_id': slot.id,
                'subject_id': False,
                'teacher_id': False,
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'de.timetable',
            'view_mode': 'form',
            'res_id': timetable.id,
        }