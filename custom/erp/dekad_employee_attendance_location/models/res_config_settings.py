from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_max_distance = fields.Float(
        string="Max Allowed Distance (m)",
        config_parameter='hr_attendance.max_distance',
    )

    def set_values(self):
        super().set_values()

        attendances = self.env['hr.attendance'].search([])

        for rec in attendances:
            rec._compute_distance_flags()

        # force write to DB (important)
        attendances.write({
            'is_checkin_exceeded': False,
        })