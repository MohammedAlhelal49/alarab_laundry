# attendance_location/models/hr_employee.py
# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Link to patient contacts (res.partner)
    patient_ids = fields.Many2many(
        'res.partner',
        'hr_employee_res_partner_rel',
        'employee_id',
        'partner_id',
        string='Assigned Patients',
        domain=[('is_company', '=', False)],
        help='List of patients assigned to this employee.'
    )

    @api.model
    def fetch_patients(self):
        """Return patient list assigned to the current employee (for JS usage)."""
        employee = self.env.user.employee_id
        if not employee:
            return []
        return [{'id': patient.id, 'name': patient.name} for patient in employee.patient_ids]

    def write(self, vals):
        """Ensure assignment-related computed fields on patients are updated if assignment changes."""
        result = super().write(vals)
        if 'patient_ids' in vals:
            for employee in self:
                for partner in employee.patient_ids:
                    patient = self.env['attendance_location.patient'].search([('partner_id', '=', partner.id)])
                    if patient:
                        patient._compute_assignment()
        return result