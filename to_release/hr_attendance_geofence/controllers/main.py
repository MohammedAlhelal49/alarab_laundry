# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.tools import float_round


class HrAttendanceGeofence(http.Controller):

    @http.route('/hr_attendance_geofence/check_location', type='json', auth='user')
    def check_location(self, latitude, longitude):
        """Pre-check whether the current employee is inside a geofence.

        Called by the mobile app before showing the check-in/check-out button.

        Args:
            latitude (float): Current GPS latitude
            longitude (float): Current GPS longitude

        Returns:
            dict: {
                'allowed': bool,
                'geofence_enabled': bool,
                'geofence_required': bool,
                'zone': { 'zone_name': str, 'distance': float, 'inside': bool } or None,
                'message': str
            }
        """
        employee = request.env.user.employee_id
        if not employee:
            return {'allowed': False, 'error': _('No employee linked to current user')}

        company = employee.company_id

        # If geofence is not enabled company-wide, always allow
        if not company.attendance_geofence_enabled:
            return {
                'allowed': True,
                'geofence_enabled': False,
                'message': _('Geofence enforcement is not enabled'),
            }

        # If this employee doesn't require geofence, allow
        if not employee.geofence_required:
            return {
                'allowed': True,
                'geofence_enabled': True,
                'geofence_required': False,
                'message': _('Geofence is not required for this employee'),
            }

        # If no zones assigned, allow (no restriction)
        if not employee.geofence_zone_ids:
            return {
                'allowed': True,
                'geofence_enabled': True,
                'geofence_required': True,
                'message': _('No geofence zones assigned to this employee'),
            }

        # Check location against zones
        result = request.env['hr.attendance.geofence.zone'].check_employee_location(
            employee.id, latitude, longitude
        )
        result['geofence_enabled'] = True
        result['geofence_required'] = True
        return result

    @http.route('/hr_attendance_geofence/attendance_action', type='json', auth='user')
    def attendance_action(self, latitude=False, longitude=False):
        """Combined geofence check + attendance action (check-in or check-out).

        This is the main endpoint the mobile app should call for attendance.
        It validates the geofence first, then performs the check-in/check-out.

        Args:
            latitude (float): Current GPS latitude
            longitude (float): Current GPS longitude

        Returns:
            dict: Employee attendance data on success, or error details
        """
        employee = request.env.user.employee_id
        if not employee:
            return {'error': _('No employee linked to current user')}

        company = employee.company_id
        device_tracking_enabled = company.attendance_device_tracking if 'attendance_device_tracking' in company._fields else True

        geo_ip_response = self._get_geo_response(
            latitude=latitude,
            longitude=longitude,
            device_tracking_enabled=device_tracking_enabled,
        )

        try:
            employee._attendance_action_change(geo_ip_response)
        except Exception as e:
            return {
                'error': str(e),
                'attendance_state': employee.attendance_state,
            }

        return {
            'id': employee.id,
            'employee_name': employee.name,
            'hours_today': float_round(employee.hours_today, precision_digits=2),
            'hours_previously_today': float_round(employee.hours_previously_today, precision_digits=2),
            'last_attendance_worked_hours': float_round(employee.last_attendance_worked_hours, precision_digits=2),
            'last_check_in': employee.last_check_in,
            'attendance_state': employee.attendance_state,
            'attendance': {
                'check_in': employee.last_attendance_id.check_in,
                'check_out': employee.last_attendance_id.check_out,
            },
        }

    @http.route('/hr_attendance_geofence/get_employee_zones', type='json', auth='user', readonly=True)
    def get_employee_zones(self):
        """Get the geofence zones assigned to the current employee.

        Called by the mobile app to draw geofence circles on the map.

        Returns:
            dict: {
                'geofence_enabled': bool,
                'geofence_required': bool,
                'zones': [{ id, name, latitude, longitude, radius, address }]
            }
        """
        employee = request.env.user.employee_id
        if not employee:
            return {'error': _('No employee linked to current user')}

        zones_data = []
        for zone in employee.geofence_zone_ids.filtered('active'):
            zones_data.append({
                'id': zone.id,
                'name': zone.name,
                'latitude': zone.latitude,
                'longitude': zone.longitude,
                'radius': zone.radius,
                'address': zone.address or '',
            })

        return {
            'geofence_enabled': employee.company_id.attendance_geofence_enabled,
            'geofence_required': employee.geofence_required,
            'zones': zones_data,
        }

    @http.route('/hr_attendance_geofence/get_employee_status', type='json', auth='user', readonly=True)
    def get_employee_status(self):
        """Get the current attendance status of the employee.
        
        Returns:
            dict: Employee attendance data
        """
        employee = request.env.user.employee_id
        if not employee:
            return {'error': _('No employee linked to current user')}
            
        return {
            'id': employee.id,
            'employee_name': employee.name,
            'hours_today': float_round(employee.hours_today, precision_digits=2),
            'hours_previously_today': float_round(employee.hours_previously_today, precision_digits=2),
            'last_attendance_worked_hours': float_round(employee.last_attendance_worked_hours, precision_digits=2),
            'last_check_in': employee.last_check_in,
            'attendance_state': employee.attendance_state,
            'attendance': {
                'check_in': employee.last_attendance_id.check_in,
                'check_out': employee.last_attendance_id.check_out,
            } if employee.last_attendance_id else None,
        }

    @staticmethod
    def _get_geo_response(latitude=False, longitude=False, device_tracking_enabled=True):
        """Build geo information dict compatible with hr.attendance fields.

        Returns a dict with keys matching the in_/out_ prefix pattern used by
        _attendance_action_change().
        """
        response = {'mode': 'systray'}

        if not device_tracking_enabled:
            return response

        try:
            location = request.env['base.geocoder']._get_localisation(latitude, longitude)
        except Exception:
            location = _("Unknown")

        response.update({
            'city': location,
            'latitude': latitude or request.geoip.location.latitude or False,
            'longitude': longitude or request.geoip.location.longitude or False,
            'ip_address': request.geoip.ip,
            'browser': request.httprequest.user_agent.browser,
        })

        return response
