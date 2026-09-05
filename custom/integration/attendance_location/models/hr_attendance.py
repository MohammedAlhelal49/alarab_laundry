# attendance_location/models/hr_attendance.py

from odoo import models, fields, api
import logging
from geopy.distance import geodesic
from odoo.http import request
_logger = logging.getLogger(__name__)

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # ========== Fields ==========

    patient_id = fields.Many2one('res.partner', string='Patient')
    in_latitude = fields.Float(string='Check-in Latitude', digits=(10, 7))
    in_longitude = fields.Float(string='Check-in Longitude', digits=(10, 7))
    out_latitude = fields.Float(string='Check-out Latitude', digits=(10, 7))
    out_longitude = fields.Float(string='Check-out Longitude', digits=(10, 7))

    checkin_distance_m = fields.Float(
        string='Check-in Distance (m)', compute='_compute_checkin_distance', store=True)
    checkout_distance_m = fields.Float(
        string='Check-out Distance (m)', compute='_compute_checkout_distance', store=True)

    patient_latitude = fields.Float(related='patient_id.gps_latitude', readonly=True)
    patient_longitude = fields.Float(related='patient_id.gps_longitude', readonly=True)

    in_ip = fields.Char(string='Check-in IP')
    out_ip = fields.Char(string='Check-out IP')
    in_localisation = fields.Char(string='Localisation', readonly=True, store=True)
    out_localisation = fields.Char(string='Localisation', readonly=True, store=True)

    # ========== Distance Computation ==========

    @api.depends('in_latitude', 'in_longitude', 'patient_id')
    def _compute_checkin_distance(self):
        for rec in self:
            try:
                if rec.patient_id and rec.in_latitude and rec.in_longitude:
                    patient_coords = (rec.patient_id.gps_latitude or 0.0, rec.patient_id.gps_longitude or 0.0)
                    rec.checkin_distance_m = geodesic(patient_coords, (rec.in_latitude, rec.in_longitude)).meters
                else:
                    rec.checkin_distance_m = 0.0
            except Exception as e:
                _logger.warning('Failed to compute check-in distance: %s', e)
                rec.checkin_distance_m = 0.0

    @api.depends('out_latitude', 'out_longitude', 'patient_id')
    def _compute_checkout_distance(self):
        for rec in self:
            try:
                if rec.patient_id and rec.out_latitude and rec.out_longitude:
                    patient_coords = (rec.patient_id.gps_latitude or 0.0, rec.patient_id.gps_longitude or 0.0)
                    rec.checkout_distance_m = geodesic(patient_coords, (rec.out_latitude, rec.out_longitude)).meters
                else:
                    rec.checkout_distance_m = 0.0
            except Exception as e:
                _logger.warning('Failed to compute check-out distance: %s', e)
                rec.checkout_distance_m = 0.0

    # ========= MAIN ATTENDANCE METHOD ===========


    @api.model
    def process_attendance_with_patient(self, patient_id=None, latitude=None, longitude=None, client_ip=None):
        employee = self.env.user.employee_id
        current_att = self.sudo().search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False)
        ], limit=1)

        localisation = self._geoip_lookup(client_ip)
        patient = self.env['res.partner'].browse(patient_id) if patient_id else None

        if current_att:
            # ========== Check-out ==========
            if current_att.patient_id and patient and current_att.patient_id.id != patient.id:
                return {'error': f"You must check out with the same patient: {current_att.patient_id.name}."}

            vals = {
                'check_out': fields.Datetime.now(),
                'out_ip': client_ip,
                'out_localisation': localisation,
                #'patient_checkout_gps': f"{patient.gps_latitude}, {patient.gps_longitude}" if patient else "0.0000000, 0.0000000",
                #'out_mode': 'dashboard' if patient else False,
            }
            if latitude and longitude:
                vals.update({'out_latitude': latitude, 'out_longitude': longitude})
            current_att.write(vals)
            return {'status': 'checked_out'}
        else:
            # ========== Check-in ==========
            new_att = employee.sudo()._attendance_action_change()
            vals = {
                'in_ip': client_ip,
                'in_localisation': localisation,
                #'patient_checkin_gps': f"{patient.gps_latitude}, {patient.gps_longitude}" if patient else "0.0000000, 0.0000000",
                'patient_id': patient.id if patient else False,
                #'in_mode': 'dashboard' if patient else False,
            }
            if latitude and longitude:
                vals.update({'in_latitude': latitude, 'in_longitude': longitude})
            new_att.write(vals)
            return {'status': 'checked_in'}

    # ========== Public RPC Entry Point ==========
    @api.model
    def location_attendance(self, patient_id=None, latitude=None, longitude=None):
        """
        Public method to allow dashboard JS to trigger attendance from browser location.
        """
        forwarded = request.httprequest.headers.get('X-Forwarded-For')
        remote = request.httprequest.remote_addr
        client_ip = forwarded.split(',')[0].strip() if forwarded else remote or '127.0.0.1'
        employee = self.env.user.employee_id
        return self.process_attendance_with_patient(
            patient_id=patient_id,
            latitude=latitude,
            longitude=longitude,
            client_ip=client_ip
        )

    # ========== GeoIP Lookup ==========
    def _geoip_lookup(self, ip):
        try:
            import geoip2.database
            reader = geoip2.database.Reader('/usr/share/GeoLite/GeoLite2-City.mmdb')
            response = reader.city(ip)
            city = response.city.name
            country = response.country.name
            return ", ".join(filter(None, [city, country]))
        except Exception as e:
            _logger.warning("GeoIP lookup failed: %s", e)
            return ''

    # ========== Map Action Buttons ==========
    def action_open_checkin_map(self):
        self.ensure_one()
        if self.in_latitude and self.in_longitude:
            return {
                'type': 'ir.actions.act_url',
                'url': f"https://www.google.com/maps?q={self.in_latitude},{self.in_longitude}",
                'target': 'new'
            }

    def action_open_checkout_map(self):
        self.ensure_one()
        if self.out_latitude and self.out_longitude:
            return {
                'type': 'ir.actions.act_url',
                'url': f"https://www.google.com/maps?q={self.out_latitude},{self.out_longitude}",
                'target': 'new'
            }

    def action_open_patient_map(self):
        self.ensure_one()
        if self.patient_latitude and self.patient_longitude:
            return {
                'type': 'ir.actions.act_url',
                'url': f"https://www.google.com/maps?q={self.patient_latitude},{self.patient_longitude}",
                'target': 'new'
            }