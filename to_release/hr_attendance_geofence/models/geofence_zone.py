# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from odoo import models, fields, api, _


class HrAttendanceGeofenceZone(models.Model):
    _name = 'hr.attendance.geofence.zone'
    _description = 'Attendance Geofence Zone'
    _order = 'name'

    name = fields.Char(string='Zone Name', required=True, help='A descriptive name for this geofence zone (e.g., Main Office, Warehouse A)')
    latitude = fields.Float(string='Latitude', digits=(10, 7), required=True, help='Center latitude of the geofence zone')
    longitude = fields.Float(string='Longitude', digits=(10, 7), required=True, help='Center longitude of the geofence zone')
    radius = fields.Float(string='Radius (meters)', required=True, default=200.0, help='Radius of the geofence zone in meters')
    address = fields.Char(string='Address', help='Optional address description for this zone')
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        'hr_employee_geofence_zone_rel',
        'zone_id',
        'employee_id',
        string='Assigned Employees',
        help='Employees who are allowed to check-in/check-out from this zone',
    )
    employee_count = fields.Integer(string='Employee Count', compute='_compute_employee_count')

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for zone in self:
            zone.employee_count = len(zone.employee_ids)

    @staticmethod
    def _haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate the great-circle distance between two points on Earth
        using the Haversine formula.

        Args:
            lat1, lon1: Coordinates of point 1 (in decimal degrees)
            lat2, lon2: Coordinates of point 2 (in decimal degrees)

        Returns:
            Distance in meters
        """
        R = 6371000  # Earth's radius in meters

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2) ** 2
             + math.cos(phi1) * math.cos(phi2)
             * math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def check_point_inside(self, latitude, longitude):
        """Check if a GPS point is inside this geofence zone.

        Args:
            latitude: Point latitude
            longitude: Point longitude

        Returns:
            dict with 'inside' (bool), 'distance' (float in meters), 'zone_name' (str)
        """
        self.ensure_one()
        distance = self._haversine_distance(
            self.latitude, self.longitude,
            latitude, longitude
        )
        return {
            'inside': distance <= self.radius,
            'distance': round(distance, 2),
            'zone_name': self.name,
            'zone_id': self.id,
        }

    @api.model
    def check_employee_location(self, employee_id, latitude, longitude):
        """Check if an employee's location is within any of their assigned geofence zones.

        Args:
            employee_id: ID of the employee
            latitude: Current latitude
            longitude: Current longitude

        Returns:
            dict with 'allowed' (bool), 'nearest_zone' (dict), 'zones_checked' (list)
        """
        employee = self.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            return {'allowed': False, 'error': _('Employee not found')}

        zones = employee.geofence_zone_ids.filtered('active')
        if not zones:
            # No zones assigned — allow by default (no restriction)
            return {'allowed': True, 'message': _('No geofence zones assigned')}

        results = []
        nearest_zone = None
        min_distance = float('inf')

        for zone in zones:
            result = zone.check_point_inside(latitude, longitude)
            results.append(result)
            if result['distance'] < min_distance:
                min_distance = result['distance']
                nearest_zone = result
            if result['inside']:
                return {
                    'allowed': True,
                    'zone': result,
                    'zones_checked': results,
                }

        return {
            'allowed': False,
            'nearest_zone': nearest_zone,
            'zones_checked': results,
            'message': _('You are outside all assigned geofence zones. Nearest zone: %(zone)s (%(distance)s m away)',
                         zone=nearest_zone['zone_name'],
                         distance=nearest_zone['distance']),
        }
