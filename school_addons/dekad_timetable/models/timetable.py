from odoo import models, fields

class DeTimetable(models.Model):
    _name = 'de.timetable'
    _description = 'School Timetable'
    _inherit = 'mail.thread'

    name = fields.Char(string="Name", required=True, tracking=True)
    academic_year_id = fields.Many2one('de.academic.year', string='Academic Year', required=True)
    academic_term_id = fields.Many2one('de.academic.term', string='Academic Term', required=True)
    classroom_id = fields.Many2one('de.classroom', string='Classroom', required=True)
    grade_id = fields.Many2one('de.grade', string='Grade', required=True)
    # session_slot_id = fields.Many2one('de.session.slot', string='Session Slot')
    # subject_id = fields.Many2one('de.subject', string='Subject', required=True)
    line_ids = fields.One2many('de.timetable.line', 'timetable_id', string='Timetable Lines')
    # teacher_id = fields.Many2one('de.teacher', string='Teacher', required=True)

    def print_timetable_report(self):
        return self.env.ref('dekad_timetable.action_report_timetable_pdf').report_action(self)
