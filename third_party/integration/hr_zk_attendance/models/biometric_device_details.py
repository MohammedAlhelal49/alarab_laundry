# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Bhagyadev KP (odoo@cybrosys.com)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
################################################################################
import datetime
import logging
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
try:
    from zk import ZK, const
except ImportError:
    _logger.error("Please Install pyzk library.")


class BiometricDeviceDetails(models.Model):
    """Model for configuring and connect the biometric device with odoo"""
    _name = 'biometric.device.details'
    _description = 'Biometric Device Details'

    name = fields.Char(string='Name', required=True, help='Record Name')
    device_ip = fields.Char(string='Device IP', required=True,
                            help='The IP address of the Device')
    port_number = fields.Integer(string='Port Number', required=True,
                                 help="The Port Number of the Device")
    address_id = fields.Many2one('res.partner', string='Working Address',
                                 help='Working address of the partner')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda
                                     self: self.env.user.company_id.id,
                                 help='Current Company')

    def device_connect(self, zk):
        """Function for connecting the device with Odoo"""
        try:
            conn = zk.connect()
            return conn
        except Exception:
            return False

    def action_test_connection(self):
        """Checking the connection status"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=30,
                password=False, ommit_ping=True)
        try:
            if zk.connect():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Successfully Connected',
                        'type': 'success',
                        'sticky': False
                    }
                }
        except Exception as error:
            raise ValidationError(f'{error}')

    def action_set_timezone(self):
        """Function to set user's timezone to device"""
        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_number
            try:
                # Connecting with the device with the ip and port provided
                zk = ZK(machine_ip, port=zk_port, timeout=15,
                        password=0,
                        force_udp=False, ommit_ping=True)
            except NameError:
                raise UserError(
                    _("Pyzk module not Found. Please install it"
                      "with 'pip3 install pyzk'."))
            conn = self.device_connect(zk)
            if conn:
                user_tz = self.env.context.get(
                    'tz') or self.env.user.tz or 'UTC'
                user_timezone_time = pytz.utc.localize(fields.Datetime.now())
                user_timezone_time = user_timezone_time.astimezone(
                    pytz.timezone(user_tz))
                conn.set_time(user_timezone_time)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Successfully Set the Time',
                        'type': 'success',
                        'sticky': False
                    }
                }
            else:
                raise UserError(_(
                    "Please Check the Connection"))

    def action_clear_attendance(self):
        """Methode to clear record from the zk.machine.attendance model and
        from the device"""
        for info in self:
            try:
                machine_ip = info.device_ip
                zk_port = info.port_number
                try:
                    # Connecting with the device
                    zk = ZK(machine_ip, port=zk_port, timeout=30,
                            password=0, force_udp=False, ommit_ping=True)
                except NameError:
                    raise UserError(_(
                        "Please install it with 'pip3 install pyzk'."))
                conn = self.device_connect(zk)
                if conn:
                    conn.enable_device()
                    clear_data = zk.get_attendance()
                    if clear_data:
                        # Clearing data in the device
                        conn.clear_attendance()
                        # Clearing data from attendance log
                        self._cr.execute(
                            """delete from zk_machine_attendance""")
                        conn.disconnect()
                    else:
                        raise UserError(
                            _('Unable to clear Attendance log.Are you sure '
                              'attendance log is not empty.'))
                else:
                    raise UserError(
                        _('Unable to connect to Attendance Device. Please use '
                          'Test Connection button to verify.'))
            except Exception as error:
                raise ValidationError(f'{error}')

    @api.model
    def cron_download(self):
        machines = self.env['biometric.device.details'].search([])
        for machine in machines:
            machine.action_download_attendance()

    def action_download_attendance(self):
        _logger.info("++++++++++++ Cron Executed ++++++++++++++")
        MIN_INTERVAL_MINUTES = 5
        AUTOCLOSE_MINUTES = 30
        SAFE_GAP_SECONDS = 60
        UAE_TZ = pytz.timezone('Asia/Dubai')
        zk_attendance = self.env['zk.machine.attendance'].sudo()
        hr_attendance = self.env['hr.attendance'].sudo()
        Employee = self.env['hr.employee'].sudo()

        def _safe_close(att, desired_dt):
            cin = fields.Datetime.from_string(att.check_in)
            min_ok = cin + datetime.timedelta(seconds=SAFE_GAP_SECONDS)
            target = desired_dt if desired_dt else min_ok
            if target < min_ok:
                target = min_ok
            att.write({'check_out': fields.Datetime.to_string(target)})

        def _close_all_open(employee, up_to_dt, tz):
            opens = hr_attendance.search([('employee_id', '=', employee.id), ('check_out', '=', False)])
            for att in opens:
                cin = fields.Datetime.from_string(att.check_in)
                desired = up_to_dt - datetime.timedelta(seconds=SAFE_GAP_SECONDS)
                try:
                    if tz.localize(cin).date() != tz.localize(up_to_dt).date():
                        desired = min(desired, cin + datetime.timedelta(minutes=AUTOCLOSE_MINUTES))
                except Exception:
                    pass
                _safe_close(att, desired)

        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_number
            try:
                zk = ZK(machine_ip, port=zk_port, timeout=20, password=0, force_udp=False, ommit_ping=True)
            except NameError:
                raise UserError(_("Pyzk module not Found. Please install it."))
            try:
                self.action_set_timezone()
            except Exception as tz_err:
                _logger.warning("Cannot set device time: %s", tz_err)
            conn = self.device_connect(zk)
            if not conn:
                raise UserError(_('Unable to connect, please check the parameters and network connections.'))
            try:
                conn.disable_device()
                users_list = conn.get_users() or []
                users = {u.user_id: u for u in users_list}
                logs = conn.get_attendance() or []
            except Exception as e:
                raise UserError(_("Failed to read from device: %s") % e)
            finally:
                try:
                    conn.enable_device()
                    conn.disconnect()
                except Exception:
                    pass
            if not logs:
                raise UserError(_('Unable to get the attendance log, please try again later.'))
            logs.sort(key=lambda l: l.timestamp)
            last_map = {}
            for rec in logs:
                matched_user = users.get(rec.user_id)
                if not matched_user:
                    continue
                employee = Employee.search([('device_id_num', '=', rec.user_id)], limit=1)
                if not employee:
                    employee = Employee.create({
                        'device_id_num': rec.user_id,
                        'name': matched_user.name or f'User {rec.user_id}',
                    })
                tz_name = employee.tz or employee.company_id.resource_calendar_id.tz or self.env.user.tz or 'UTC'
                tz = pytz.timezone(tz_name)
                local_dt = tz.localize(rec.timestamp, is_dst=None)
                utc_dt = local_dt.astimezone(pytz.utc).replace(tzinfo=None)
                utc_str = fields.Datetime.to_string(utc_dt)
                log_time = local_dt.astimezone(UAE_TZ).strftime('%Y-%m-%d %H:%M:%S')
                if not zk_attendance.search([('device_id_num', '=', rec.user_id), ('punching_time', '=', utc_str)],
                                            limit=1):
                    zk_attendance.create({
                        'employee_id': employee.id,
                        'device_id_num': rec.user_id,
                        'attendance_type': str(rec.status),
                        'punch_type': '0',
                        'punching_time': utc_str,
                        'address_id': info.address_id.id
                    })
                if employee.id not in last_map:
                    last_map[employee.id] = hr_attendance.search(
                        [('employee_id', '=', employee.id)], order="check_in desc", limit=1
                    )
                last_att = last_map[employee.id]
                if not last_att or last_att.check_out:
                    _close_all_open(employee, utc_dt, tz)
                    prev = hr_attendance.search(
                        [('employee_id', '=', employee.id)], order="check_in desc", limit=1
                    )
                    new_cin_dt = utc_dt
                    if prev and prev.check_out:
                        prev_out = fields.Datetime.from_string(prev.check_out)
                        if new_cin_dt <= prev_out:
                            new_cin_dt = prev_out + datetime.timedelta(seconds=SAFE_GAP_SECONDS)
                    new_att = hr_attendance.create({
                        'employee_id': employee.id,
                        'check_in': fields.Datetime.to_string(new_cin_dt),
                    })
                    last_map[employee.id] = new_att
                    _logger.info(f"[NEW CHECK-IN] {employee.name} | {log_time}")
                    continue
                cin_dt = fields.Datetime.from_string(last_att.check_in)
                if utc_dt <= cin_dt:
                    _logger.info(f"[SKIP] {employee.name} | punch earlier than open check-in | {log_time}")
                    continue
                diff_minutes = (utc_dt - cin_dt).total_seconds() / 60.0
                if diff_minutes < MIN_INTERVAL_MINUTES:
                    _logger.info(f"[SKIP] {employee.name} | duplicate within {MIN_INTERVAL_MINUTES} mins | {log_time}")
                    continue
                emp_day_in = tz.localize(cin_dt).date()
                emp_day_now = tz.localize(utc_dt).date()
                if emp_day_now != emp_day_in:
                    desired = cin_dt + datetime.timedelta(minutes=AUTOCLOSE_MINUTES)
                    if desired >= utc_dt:
                        desired = utc_dt - datetime.timedelta(seconds=SAFE_GAP_SECONDS)
                    _safe_close(last_att, desired)
                    try:
                        last_att.message_post(
                            body=(f"[Auto-Closed] Closed at {fields.Datetime.to_string(desired)} "
                                  f"(employee tz: {tz_name}).")
                        )
                    except Exception:
                        pass
                    new_cin_dt = utc_dt
                    prev_out = fields.Datetime.from_string(last_att.check_out) if last_att.check_out else desired
                    if new_cin_dt <= prev_out:
                        new_cin_dt = prev_out + datetime.timedelta(seconds=SAFE_GAP_SECONDS)
                    new_att = hr_attendance.create({
                        'employee_id': employee.id,
                        'check_in': fields.Datetime.to_string(new_cin_dt),
                    })
                    last_map[employee.id] = new_att
                    _logger.info(f"[AUTO-CLOSE & NEW DAY CHECK-IN] {employee.name} | {log_time}")
                    continue
                _safe_close(last_att, utc_dt)
                _logger.info(f"[CHECK-OUT] {employee.name} | {log_time}")
        return True
    def action_restart_device(self):
        """For restarting the device"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=15,
                password=0,
                force_udp=False, ommit_ping=True)
        self.device_connect(zk).restart()

    def reset_employee_device_id_num(self):
        for rec in self.env['hr.employee'].search([]):
            rec.device_id_num = ''
        # for rec in self.env['hr.employee.public'].search([]):
        #     rec.device_id_num = ''