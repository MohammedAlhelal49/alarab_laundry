from odoo import models, fields

class AttendanceLocationPatientSelection(models.TransientModel):
    _name = 'attendance.location.patient.selection'
    _description = 'Select Patient for Attendance'

    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Attendance',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )
    patient_id = fields.Many2one(
        'res.partner',
        string='Patient',
        required=True,
        domain=lambda self: [
            ('id', 'in', self.env.user.employee_id.patient_ids.ids)
        ]
    )

    def action_confirm(self):
        self.ensure_one()
        self.attendance_id.write({
            'patient_id': self.patient_id.id,
            'in_latitude': self.env.context.get('latitude') or self.attendance_id.in_latitude,
            'in_longitude': self.env.context.get('longitude') or self.attendance_id.in_longitude,
        })
        return {'type': 'ir.actions.act_window_close'}
