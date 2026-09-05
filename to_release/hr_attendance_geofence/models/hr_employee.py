# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    geofence_zone_ids = fields.Many2many(
        'hr.attendance.geofence.zone',
        'hr_employee_geofence_zone_rel',
        'employee_id',
        'zone_id',
        string='Geofence Zones',
        help='Geofence zones where this employee is allowed to check-in/check-out. '
             'Leave empty to allow check-in from anywhere.',
        groups='hr_attendance.group_hr_attendance_officer',
    )
    geofence_required = fields.Boolean(
        string='Geofence Required',
        default=True,
        help='If enabled, this employee must be inside an assigned geofence zone to check-in/check-out. '
             'Disable for remote workers or traveling employees.',
        groups='hr_attendance.group_hr_attendance_officer',
    )

    def _attendance_action_change(self, geo_information=None):
        """Override to add geofence validation before check-in/check-out.

        The geofence check runs only when ALL of these conditions are met:
        1. The company has geofence enforcement enabled
        2. The employee has geofence_required = True
        3. The employee has at least one geofence zone assigned
        4. GPS coordinates are provided in geo_information
        """
        self.ensure_one()

        # Check if geofence validation is needed
        if (self.company_id.attendance_geofence_enabled
                and self.geofence_required
                and self.geofence_zone_ids):

            _logger.info(f"Geofence check for {self.name}: Validating location...")

            if not geo_information:
                _logger.warning(f"Geofence check for {self.name} FAILED: No geo_information provided.")
                raise exceptions.ValidationError(_('Location information is required for geofence validation. Please enable GPS/Location.'))

            latitude = geo_information.get('latitude')
            longitude = geo_information.get('longitude')
            
            _logger.info(f"Geofence check for {self.name}: Received lat={latitude}, lng={longitude}")

            if not latitude or not longitude:
                _logger.warning(f"Geofence check for {self.name} FAILED: Invalid coordinates.")
                raise exceptions.ValidationError(_('Invalid location data. Latitude and longitude are required.'))

            result = self.env['hr.attendance.geofence.zone'].check_employee_location(
                self.id, float(latitude), float(longitude)
            )
            
            if not result.get('allowed'):
                _logger.warning(f"Geofence check for {self.name} FAILED: Outside assigned zones. Result: {result}")
                raise exceptions.ValidationError(
                    result.get('message', _('You are outside your assigned geofence zone. Check-in/Check-out is not allowed.'))
                )
            
            _logger.info(f"Geofence check for {self.name} PASSED: {result}")
        else:
            _logger.info(f"Geofence check bypassed for {self.name}. Enabled: {self.company_id.attendance_geofence_enabled}, Required: {self.geofence_required}, HasZones: {bool(self.geofence_zone_ids)}")



        # Call the original method to perform the actual check-in/check-out
        return super()._attendance_action_change(geo_information)
