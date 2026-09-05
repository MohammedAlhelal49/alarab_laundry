from odoo import models, fields, api
import logging
from geopy.distance import geodesic
from odoo.http import request

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # ========== Fields ==========

    in_latitude = fields.Float(string='Check-in Latitude', digits=(10, 7))
    in_longitude = fields.Float(string='Check-in Longitude', digits=(10, 7))
    out_latitude = fields.Float(string='Check-out Latitude', digits=(10, 7))
    out_longitude = fields.Float(string='Check-out Longitude', digits=(10, 7))

    # Employee location (related)
    employee_latitude = fields.Float(
        related='employee_id.gps_latitude',
        readonly=True,
        store=True
    )
    employee_longitude = fields.Float(
        related='employee_id.gps_longitude',
        readonly=True,
        store=True
    )

    checkin_distance_m = fields.Float(
        string='Check-in Distance (m)',
        compute='_compute_checkin_distance',
        digits=(16, 5
                ),
        store=True
    )

    checkout_distance_m = fields.Float(
        string='Check-out Distance (m)',
        compute='_compute_checkout_distance',
        digits=(16, 5),
        store=True
    )

    in_ip = fields.Char(string='Check-in IP')
    out_ip = fields.Char(string='Check-out IP')
    in_localisation = fields.Char(string='Localisation', readonly=True, store=True)
    out_localisation = fields.Char(string='Localisation', readonly=True, store=True)

    is_checkin_exceeded = fields.Boolean(
        compute="_compute_distance_flags",
        store=False
    )

    is_checkout_exceeded = fields.Boolean(
        compute="_compute_distance_flags",
        store=False
    )
    is_distance_exceeded = fields.Boolean(
        string="Distance Exceeded",
        compute="_compute_distance_flags",
        search="_search_is_distance_exceeded",
        store=False
    )

    @api.depends('checkin_distance_m', 'checkout_distance_m')
    def _compute_distance_flags(self):
        param = float(
            self.env['ir.config_parameter'].sudo().get_param(
                'hr_attendance.max_distance', 0
            )
        )

        for rec in self:
            if param <= 0:
                rec.is_checkin_exceeded = False
                rec.is_checkout_exceeded = False
                rec.is_distance_exceeded = False
                continue

            rec.is_checkin_exceeded = rec.checkin_distance_m > param
            rec.is_checkout_exceeded = rec.checkout_distance_m > param

            rec.is_distance_exceeded = (
                    rec.is_checkin_exceeded
                    or rec.is_checkout_exceeded
            )

    # ========== Distance Computation ==========

    @api.depends(
        'in_latitude',
        'in_longitude',
        'employee_id',
        'employee_id.gps_latitude',
        'employee_id.gps_longitude',
    )
    def _compute_checkin_distance(self):
        for rec in self:
            emp = rec.employee_id

            if (
                    not emp
                    or not emp.gps_latitude
                    or not emp.gps_longitude
                    or not rec.in_latitude
                    or not rec.in_longitude
            ):
                rec.checkin_distance_m = 0.0
                continue

            rec.checkin_distance_m = geodesic(
                (emp.gps_latitude, emp.gps_longitude),
                (rec.in_latitude, rec.in_longitude)
            ).meters


    @api.depends('out_latitude', 'out_longitude', 'employee_id')
    def _compute_checkout_distance(self):
        for rec in self:
            try:
                emp = rec.employee_id

                #  Skip if employee GPS not set
                if not emp or not emp.gps_latitude or not emp.gps_longitude:
                    rec.checkout_distance_m = 0.0
                    continue

                if rec.out_latitude and rec.out_longitude:
                    rec.checkout_distance_m = geodesic(
                        (emp.gps_latitude, emp.gps_longitude),
                        (rec.out_latitude, rec.out_longitude)
                    ).meters
                else:
                    rec.checkout_distance_m = 0.0

            except Exception as e:
                _logger.warning('Failed to compute check-out distance: %s', e)
                rec.checkout_distance_m = 0.0


    # ========= MAIN ATTENDANCE METHOD ===========

    @api.model
    def process_attendance(self, latitude=None, longitude=None, client_ip=None):
        real_uid = self.env.uid
        company = self.env.company

        # =========================================================
        # SECURITY:
        # Determine employee from the authenticated user BEFORE sudo
        # =========================================================
        employee = self.env['hr.employee'].sudo().search([
            ('user_id', '=', real_uid),
            ('company_id', '=', company.id),
        ], limit=1)

        if not employee:
            _logger.warning(
                "[Attendance] No employee for uid=%s company=%s",
                real_uid,
                company.id,
            )
            return {
                'status': 'error',
                'message': (
                        'No employee is linked to your user in the current company: %s'
                        % company.name
                ),
            }

        localisation = self._geoip_lookup(client_ip)

        Attendance = self.env['hr.attendance'].sudo()

        # =========================================================
        # Find existing open attendance using sudo
        # =========================================================
        current_att = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False),
        ], order='check_in desc', limit=1)

        # =========================================================
        # IMPORTANT
        # employee is sudo, therefore Odoo attendance creation /
        # checkout runs as superuser and bypasses the officer rule.
        # =========================================================
        attendance = employee.sudo()._attendance_action_change()

        # =========================================================
        # CHECK OUT
        # =========================================================
        if current_att:
            vals = {
                'out_ip': client_ip or '',
                'out_localisation': localisation or '',
            }

            if latitude is not None and longitude is not None:
                vals.update({
                    'out_latitude': float(latitude),
                    'out_longitude': float(longitude),
                })

            attendance.sudo().write(vals)

            return {
                'status': 'checked_out',
                'attendance_id': attendance.id,
            }

        # =========================================================
        # CHECK IN
        # =========================================================
        vals = {
            'in_ip': client_ip or '',
            'in_localisation': localisation or '',
        }

        if latitude is not None and longitude is not None:
            vals.update({
                'in_latitude': float(latitude),
                'in_longitude': float(longitude),
            })

        attendance.sudo().write(vals)

        return {
            'status': 'checked_in',
            'attendance_id': attendance.id,
        }

    # ========== Public RPC Entry Point ==========

    @api.model
    def location_attendance(self, latitude=None, longitude=None):
        forwarded = request.httprequest.headers.get('X-Forwarded-For')
        remote = request.httprequest.remote_addr
        client_ip = forwarded.split(',')[0].strip() if forwarded else remote or '127.0.0.1'

        return self.process_attendance(
            latitude=latitude,
            longitude=longitude,
            client_ip=client_ip
        )

    # ========== GeoIP Lookup ==========

    def _geoip_lookup(self, ip):
        if not ip:
            return ''

        try:
            import geoip2.database

            with geoip2.database.Reader(
                    '/usr/share/GeoLite/GeoLite2-City.mmdb'
            ) as reader:
                response = reader.city(ip)

                city = response.city.name
                country = response.country.name

                return ", ".join(
                    filter(None, [city, country])
                )

        except Exception as e:
            _logger.warning(
                "GeoIP lookup failed for %s: %s",
                ip,
                e
            )
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

    def action_open_employee_map(self):
        self.ensure_one()
        if self.employee_latitude and self.employee_longitude:
            return {
                'type': 'ir.actions.act_url',
                'url': f"https://www.google.com/maps?q={self.employee_latitude},{self.employee_longitude}",
                'target': 'new'
            }

    def _search_is_distance_exceeded(self, operator, value):
        max_distance = float(
            self.env['ir.config_parameter'].sudo().get_param(
                'hr_attendance.max_distance', 0
            )
        )

        if max_distance <= 0:
            return [('id', '=', 0)]

        return [
            '|',
            ('checkin_distance_m', '>', max_distance),
            ('checkout_distance_m', '>', max_distance),
        ]