# attendance_location/models/res_partner.py

from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Indicates if this contact is a patient
    is_patient = fields.Boolean(
        string='Is Patient',
        default=False,
        help="Indicates whether this contact is considered a patient."
    )

    # Link to assigned employee
    employee_patient_id = fields.Many2one(
        'hr.employee',
        string='Assigned Employee',
        ondelete='set null',
        index=True,
        help='Employee responsible for this patient.'
    )

    # GPS coordinates
    gps_latitude = fields.Float(
        string='GPS Latitude',
        digits=(10, 7),
        help='Latitude coordinate of the contact.'
    )
    gps_longitude = fields.Float(
        string='GPS Longitude',
        digits=(10, 7),
        help='Longitude coordinate of the contact.'
    )

    # Last time GPS was updated
    gps_last_updated = fields.Datetime(
        string='Last GPS Update',
        readonly=True,
        help='Timestamp when GPS location was last updated.'
    )

    # Computed Google Maps URL
    gps_location_url = fields.Char(
        string='Google Maps Link',
        compute='_compute_location_url',
        store=True,
        help='Generated Google Maps URL based on latitude and longitude.'
    )

    @api.depends('gps_latitude', 'gps_longitude')
    def _compute_location_url(self):
        """
        Compute a Google Maps link from GPS coordinates.
        """
        for rec in self:
            if rec.gps_latitude and rec.gps_longitude:
                rec.gps_location_url = f"https://www.google.com/maps?q={rec.gps_latitude},{rec.gps_longitude}"
            else:
                rec.gps_location_url = ''

    def action_get_gps_coordinates(self):
        """
        Trigger client-side geolocation request (handled by JS).
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'get_gps_coordinates',
            'context': {'partner_id': self.id},
        }

    def action_open_gps_location(self):
        """
        Open stored GPS location in Google Maps.
        """
        self.ensure_one()
        if self.gps_location_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.gps_location_url,
                'target': 'new',
            }