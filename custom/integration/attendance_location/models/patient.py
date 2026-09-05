# attendance_location/models/patient.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Patient(models.Model):
    _name = 'attendance_location.patient'
    _inherits = {'res.partner': 'partner_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Patient'

    # Related contact
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        required=True,
        ondelete='cascade'
    )

    # Read-only personal info from partner
    phone = fields.Char(related='partner_id.phone', readonly=True)
    email = fields.Char(related='partner_id.email', readonly=True)
    street = fields.Char(related='partner_id.street', readonly=True)
    city = fields.Char(related='partner_id.city', readonly=True)
    gps_latitude = fields.Float(related='partner_id.gps_latitude', readonly=True)
    gps_longitude = fields.Float(related='partner_id.gps_longitude', readonly=True)

    # Medical notes
    medical_notes = fields.Text(string='Medical Notes')
    medical_notes_last_updated = fields.Datetime(string='Last Notes Update', readonly=True)

    # Medical note history records
    medical_note_history_ids = fields.One2many(
        'attendance_location.medical_note_history',
        'patient_id',
        string='Medical Note History'
    )

    # Assigned employee info
    assigned_employee_count = fields.Integer(
        string='Assigned Employees Count',
        compute='_compute_assignment',
        store=True
    )
    is_assigned = fields.Boolean(
        string='Is Assigned',
        compute='_compute_assignment',
        store=True
    )
    assigned_employee_ids = fields.Many2many(
        'hr.employee',
        compute='_compute_assignment',
        string='Assigned Employees',
        store=False
    )

    # Prevent duplicate patient records per contact
    _sql_constraints = [
        ('unique_partner', 'UNIQUE(partner_id)', 'This contact is already registered as a patient.')
    ]

    @api.depends('partner_id')
    def _compute_assignment(self):
        """Compute employee assignment stats for each patient."""
        for rec in self:
            employees = self.env['hr.employee'].search([
                ('patient_ids', 'in', [rec.partner_id.id])
            ])
            rec.assigned_employee_count = len(employees)
            rec.is_assigned = bool(employees)
            rec.assigned_employee_ids = employees.ids

    @api.model
    def create(self, vals):
        """Prevent duplicate patients for same contact on creation."""
        partner_id = vals.get('partner_id')
        if partner_id and self.search_count([('partner_id', '=', partner_id)]):
            raise ValidationError("This contact is already registered as a patient.")
        return super().create(vals)

    def write(self, vals):
        """Prevent duplicate patients for same contact on write."""
        if 'partner_id' in vals:
            for rec in self:
                if self.search_count([
                    ('partner_id', '=', vals['partner_id']),
                    ('id', '!=', rec.id)
                ]):
                    raise ValidationError("This contact is already registered as a patient.")
        if 'medical_notes' in vals:
            vals['medical_notes_last_updated'] = fields.Datetime.now()
        return super().write(vals)

    def action_view_note_history(self):
        """Open note history for current patient."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Medical Notes History',
            'res_model': 'attendance_location.medical_note_history',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
            'target': 'current',
        }