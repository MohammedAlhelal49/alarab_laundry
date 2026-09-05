# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the1`
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import pandas as pd
from collections import defaultdict
from datetime import timedelta, datetime, date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.http import request
from odoo.tools import float_utils
from odoo.tools import format_duration
from pytz import utc
import geoip2.database
from geoip2.errors import AddressNotFoundError
import logging
from odoo import http

ROUNDING_FACTOR = 16
_logger = logging.getLogger(__name__)

class HrEmployee(models.Model):
    """ Inherit hr_employee to add birthday field and custom methods. """
    _inherit = 'hr.employee'

    birthday = fields.Date(string='Date of Birth', groups="base.group_user",
                           help="Birthday of employee")

    @api.model
    def _get_geoip_info(self, ip=None, latitude=None, longitude=None):
        """
        Retrieves location from the GeoLite2 database.
        If GPS coordinates are provided, this method is not used
        for the city and country, and only the IP will be used.
        """
        geoip_path = '/home/server/programming/credentials_files/Files/GeoLite2-City.mmdb'
        _logger.info("Starting GeoIP lookup with latitude=%s, longitude=%s, ip=%s", latitude, longitude, ip)
        try:
            with geoip2.database.Reader(geoip_path) as reader:
                if ip:
                    _logger.info("Performing GeoIP lookup using IP address.")
                    response = reader.city(ip)
                    result = {
                        'latitude': response.location.latitude or False,
                        'longitude': response.location.longitude or False,
                        'city': response.city.name or _('Unknown'),
                        'country': response.country.name or _('Unknown'),
                    }
                    _logger.info("GeoIP (IP) lookup result: %s", result)
                    return result
        except AddressNotFoundError:
            _logger.warning("Location not found in GeoLite2 database.")
        except Exception as e:
            _logger.error("GeoIP lookup error: %s", e)

        fallback_result = {
            'latitude': latitude or False,
            'longitude': longitude or False,
            'city': _('Unknown'),
            'country': _('Unknown'),
        }
        _logger.info("Returning fallback GeoIP result: %s", fallback_result)
        return fallback_result

    @api.model
    def check_user_has_employee(self):
        return bool(
            self.env['hr.employee'].search_count([
                ('user_id', '=', self.env.uid),
                ('company_id', '=', self.env.company.id),
            ])
        )

    def attendance_manual(self, *args, **kwargs):
        _logger.info(
            "[HRMS Dashboard] attendance_manual user=%s uid=%s",
            self.env.user.name,
            self.env.uid,
        )

        # =========================================================
        # IMPORTANT:
        # Find ONLY the employee belonging to the logged-in user.
        # sudo() is used for access, but the user cannot choose
        # another employee.
        # =========================================================
        employee = self.env['hr.employee'].sudo().search([
            ('user_id', '=', self.env.uid),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        if not employee:
            return {
                'success': False,
                'error': _('No employee is linked to your user.'),
            }

        # =========================================================
        # GPS
        # =========================================================
        latitude = None
        longitude = None

        if len(args) >= 2:
            try:
                latitude = float(args[0])
                longitude = float(args[1])
            except (ValueError, TypeError):
                pass

        # =========================================================
        # IP
        # =========================================================
        ip_address = (
                request.httprequest.headers.get('X-Real-IP')
                or request.httprequest.remote_addr
                or '127.0.0.1'
        )

        # =========================================================
        # GEO LOCATION
        # =========================================================
        if (
                latitude is not None
                and longitude is not None
                and (latitude != 0.0 or longitude != 0.0)
        ):
            ip_geo = self._get_geoip_info(ip=ip_address)

            geoip_info = {
                'latitude': latitude,
                'longitude': longitude,
                'city': ip_geo.get('city'),
                'country': ip_geo.get('country'),
            }
        else:
            geoip_info = self._get_geoip_info(ip=ip_address)

        browser = request.httprequest.user_agent.browser or ''

        # =========================================================
        # VERY IMPORTANT:
        # sudo() bypasses the Attendance Officer record rule.
        # =========================================================
        Attendance = self.env['hr.attendance'].sudo()

        open_attendance = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False),
        ], order='check_in desc', limit=1)

        # =========================================================
        # CHECK OUT
        # =========================================================
        if open_attendance:
            open_attendance.sudo().write({
                'check_out': fields.Datetime.now(),

                'out_latitude': geoip_info.get('latitude'),
                'out_longitude': geoip_info.get('longitude'),
                'out_city': geoip_info.get('city'),
                'out_country_name': geoip_info.get('country'),

                'out_ip_address': ip_address,
                'out_browser': browser,
                'out_mode': 'kiosk',
            })

            _logger.info(
                "[HRMS Dashboard] CHECK OUT employee=%s attendance=%s",
                employee.id,
                open_attendance.id,
            )

            return {
                'success': True,
                'status': 'checked_out',
                'attendance_id': open_attendance.id,
            }

        # =========================================================
        # CHECK IN
        # =========================================================
        attendance = Attendance.sudo().create({
            'employee_id': employee.id,
            'check_in': fields.Datetime.now(),

            'in_latitude': geoip_info.get('latitude'),
            'in_longitude': geoip_info.get('longitude'),
            'in_city': geoip_info.get('city'),
            'in_country_name': geoip_info.get('country'),

            'in_ip_address': ip_address,
            'in_browser': browser,
            'in_mode': 'kiosk',
        })

        _logger.info(
            "[HRMS Dashboard] CHECK IN employee=%s attendance=%s",
            employee.id,
            attendance.id,
        )

        return {
            'success': True,
            'status': 'checked_in',
            'attendance_id': attendance.id,
        }

    @api.model
    def check_user_group(self):
        """To check the user is a hr manager or not"""
        uid = request.session.uid
        user = self.env['res.users'].sudo().search([('id', '=', uid)], limit=1)
        if user.has_group('hr.group_hr_manager'):
            return True
        else:
            return False



    @api.model
    def get_user_employee_details(self):
        if self.check_user_has_employee():
            """To fetch the details of employee"""
            uid = request.session.uid
            employee = self.env['hr.employee'].search_read([
                ('user_id', '=', self.env.uid),
                ('company_id', '=', self.env.company.id),
            ], limit=1)

            if not employee:
                return []

            attendance = self.env['hr.attendance'].sudo().search_read(
                [('employee_id', '=', employee[0]['id'])],
                fields=['id', 'check_in', 'check_out', 'worked_hours'],
                order='check_in desc',
            )

            attendance_line = []

            for line in attendance:
                if not line['check_in']:
                    continue

                # Check In
                check_in_dubai = fields.Datetime.context_timestamp(
                    self.with_context(tz='Asia/Dubai'),
                    line['check_in']
                )

                # Check Out may still be empty
                check_out_dubai = False

                if line['check_out']:
                    check_out_dubai = fields.Datetime.context_timestamp(
                        self.with_context(tz='Asia/Dubai'),
                        line['check_out']
                    )

                val = {
                    'id': line['id'],
                    'date': check_in_dubai.strftime('%Y-%m-%d'),
                    'sign_in': check_in_dubai.strftime('%H:%M'),

                    # Empty until employee checks out
                    'sign_out': (
                        check_out_dubai.strftime('%H:%M')
                        if check_out_dubai
                        else ''
                    ),

                    # Empty until employee checks out
                    'worked_hours': (
                        format_duration(line['worked_hours'])
                        if line['check_out']
                        else ''
                    ),
                }

                attendance_line.append(val)

            leaves = self.env['hr.leave'].sudo().search_read(
                [('employee_id', '=', employee[0]['id'])],
                fields=['request_date_from', 'request_date_to', 'state',
                        'holiday_status_id'])
            for line in leaves:
                line['type'] = line.pop('holiday_status_id')[1]
                if line['state'] == 'confirm':
                    line['state'] = 'To Approve'
                    line['color'] = 'orange'
                elif line['state'] == 'validate1':
                    line['state'] = 'Second Approval'
                    line['color'] = '#7CFC00'
                elif line['state'] == 'validate':
                    line['state'] = 'Approved'
                    line['color'] = 'green'
                elif line['state'] == 'cancel':
                    line['state'] = 'Cancelled'
                    line['color'] = 'red'
                else:
                    line['state'] = 'Refused'
                    line['color'] = 'red'
            expense = self.env['hr.expense'].sudo().search_read(
                [('employee_id', '=', employee[0]['id'])],
                fields=['name', 'date', 'state', 'total_amount', 'currency_id',])
            for line in expense:
                # Currency information
                if line.get('currency_id'):
                    currency = self.env['res.currency'].sudo().browse(
                        line['currency_id'][0]
                    )

                    line['currency_name'] = currency.name
                    line['currency_symbol'] = currency.symbol or currency.name
                    line['currency_position'] = currency.position
                else:
                    line['currency_name'] = ''
                    line['currency_symbol'] = ''
                    line['currency_position'] = 'after'

                if line['state'] == 'draft':
                    line['state'] = 'To Report'
                    line['color'] = '#17A2B8'
                elif line['state'] == 'reported':
                    line['state'] = 'To Submit'
                    line['color'] = '#17A2B8'
                elif line['state'] == 'submitted':
                    line['state'] = 'Submitted'
                    line['color'] = '#FFAC00'
                elif line['state'] == 'approved':
                    line['state'] = 'Approved'
                    line['color'] = '#28A745'
                elif line['state'] == 'done':
                    line['state'] = 'Done'
                    line['color'] = '#28A745'
                else:
                    line['state'] = 'Refused'
                    line['color'] = 'red'
            leaves_to_approve = self.env['hr.leave'].sudo().search_count(
                [('state', 'in', ['confirm', 'validate1'])])
            today = datetime.strftime(datetime.today(), '%Y-%m-%d')
            query = """
            select count(id)
            from hr_leave
            WHERE (hr_leave.date_from::DATE,hr_leave.date_to::DATE) 
            OVERLAPS ('%s', '%s') and
            state='validate'""" % (today, today)
            cr = self._cr
            cr.execute(query)
            leaves_today = cr.fetchall()
            first_day = date.today().replace(day=1)
            last_day = (date.today() + relativedelta(months=1, day=1)) - timedelta(
                1)
            query = """
                    select count(id)
                    from hr_leave
                    WHERE (hr_leave.date_from::DATE,hr_leave.date_to::DATE) 
                    OVERLAPS ('%s', '%s')
                    and  state='validate'""" % (first_day, last_day)
            cr = self._cr
            cr.execute(query)
            leaves_this_month = cr.fetchall()
            leaves_alloc_req = self.env['hr.leave.allocation'].sudo().search_count(
                [('state', 'in', ['confirm', 'validate1'])])
            timesheet_count = self.env['account.analytic.line'].sudo().search_count(
                [('project_id', '!=', False), ('user_id', '=', uid)])
            timesheet_view_id = self.env.ref(
                'hr_timesheet.hr_timesheet_line_search')
            job_applications = self.env['hr.applicant'].sudo().search_count([])
            # ---------------------------------------------------------
            # Total approved leave days for logged-in employee
            # ---------------------------------------------------------
            # ---------------------------------------------------------
            # Total approved leave days for logged-in employee
            # ---------------------------------------------------------
            employee_id = employee[0]['id']

            approved_leaves = self.env['hr.leave'].sudo().search([
                ('employee_id', '=', employee_id),
                ('state', '=', 'validate'),
            ])

            total_leave_days = sum(
                approved_leaves.mapped('number_of_days')
            )

            total_leave_days = round(total_leave_days, 2)

            _logger.info(
                "[HRMS Dashboard] Employee ID %s total approved leave days: %s",
                employee_id,
                total_leave_days,
            )

            if employee[0]['birthday']:
                diff = relativedelta(datetime.today(), employee[0]['birthday'])
                age = diff.years
            else:
                age = False
            if employee[0]['joining_date']:
                diff = relativedelta(datetime.today(),
                                     employee[0]['joining_date'])
                years = diff.years
                months = diff.months
                days = diff.days
                experience = '{} years {} months {} days'.format(years, months,
                                                                 days)
            else:
                experience = False
            if employee:
                data = {
                    'total_leave_days': total_leave_days,
                    'leaves_to_approve': leaves_to_approve,
                    'leaves_today': leaves_today,
                    'leaves_this_month': leaves_this_month,
                    'leaves_alloc_req': leaves_alloc_req,
                    'emp_timesheets': timesheet_count,
                    'job_applications': job_applications,
                    'timesheet_view_id': timesheet_view_id,
                    'experience': experience,
                    'age': age,
                    'attendance_lines': attendance_line,
                    'leave_lines': leaves,
                    'expense_lines': expense
                }
                employee[0].update(data)
            return employee


    @api.model
    def get_upcoming(self):
        if self.check_user_has_employee():
            """It returns upcoming events, announcements and birthday"""
            cr = self._cr
            uid = request.session.uid
            employee = self.env['hr.employee'].search([
                ('user_id', '=', uid),
                ('company_id', '=', self.env.company.id),
            ], limit=1)

            if not employee:
                return {
                    'birthday': [],
                    # 'event': [],
                    'announcement': [],
                }
            today = fields.Date.today()
            birthday_employees = self.env['hr.employee'].search_read(
                [('birthday', '!=', False)], fields=['id', 'name', 'birthday'], order='birthday ASC', limit=4)

            for emp in birthday_employees:
                if emp['birthday'].month == today.month and emp[
                    'birthday'].day == today.day:
                    emp['is_birthday'] = True
                else:
                    emp_birthday = emp['birthday'].replace(year=today.year)
                    emp['days'] = (emp_birthday - today).days
            announcements = self.env['hr.announcement'].search_read(
                [('state', '=', 'approved'),
                 ('date_start', '<=', fields.Date.today()),
                 '|', ('is_announcement', '=', True),
                 '|', '|',
                 ('employee_ids', 'in', employee.id),
                 ('department_ids', 'in', employee.department_id.id),
                 ('position_ids', 'in', employee.job_id.id),
                 ], fields=['announcement_reason', 'date_start', 'date_end'])

            # lang = f"'{self.env.context['lang']}'"
            # cr.execute("""select e.id, e.name ->> e.lang as name, e.date_begin,
            #  e.date_end,rp.name as location
            # from event_event e
            # inner join res_partner rp
            # on e.address_id = rp.id
            # and (e.date_begin >= now())
            # order by e.date_begin""")
            # event = cr.fetchall()
            return {
                'birthday': birthday_employees,
                # 'event': event,
                'announcement': announcements
            }

    @api.model
    def get_dept_employee(self):
        if self.check_user_has_employee():
            """Retrieve the details of employees in each department."""
            cr = self._cr
            cr.execute("""select department_id, hr_department.name,count(*)
            from hr_employee join hr_department on 
            hr_department.id=hr_employee.department_id
            group by hr_employee.department_id,hr_department.name""")
            dat = cr.fetchall()
            data = []
            for i in range(0, len(dat)):
                data.append(
                    {'label': list(dat[i][1].values())[0], 'value': dat[i][2]})
            return data

    @api.model
    def get_employee_monthly_leave(self):
        """
        Return monthly approved leave days for the employee
        connected to the currently logged-in dashboard user.

        Last 6 months including current month.
        """

        # ---------------------------------------------------------
        # Find employee connected to logged-in user/current company
        # ---------------------------------------------------------
        employee = self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        if not employee:
            return []

        today = fields.Date.context_today(self)

        current_month_start = today.replace(day=1)

        first_month_start = (
                current_month_start - relativedelta(months=5)
        )

        next_month_start = (
                current_month_start + relativedelta(months=1)
        )

        # ---------------------------------------------------------
        # Create six month buckets
        # ---------------------------------------------------------
        result = []

        for i in range(6):
            month_start = (
                    first_month_start + relativedelta(months=i)
            )

            result.append({
                'month': month_start.strftime('%b %Y'),
                'year': month_start.year,
                'month_number': month_start.month,
                'days': 0.0,
            })

        # ---------------------------------------------------------
        # ONLY this employee's approved leaves
        # ---------------------------------------------------------
        leaves = self.env['hr.leave'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),

            # Leave overlaps our 6-month period
            ('request_date_from', '<', next_month_start),
            ('request_date_to', '>=', first_month_start),
        ])

        _logger.info(
            "[HRMS Dashboard] Employee %s (%s): "
            "found %s approved leaves between %s and %s",
            employee.name,
            employee.id,
            len(leaves),
            first_month_start,
            next_month_start,
        )

        # ---------------------------------------------------------
        # Split leaves into their corresponding months
        # ---------------------------------------------------------
        for leave in leaves:

            if not leave.request_date_from or not leave.request_date_to:
                continue

            for bucket in result:

                month_start = date(
                    bucket['year'],
                    bucket['month_number'],
                    1,
                )

                month_end_exclusive = (
                        month_start + relativedelta(months=1)
                )

                overlap_start = max(
                    leave.request_date_from,
                    month_start,
                )

                overlap_end_exclusive = min(
                    leave.request_date_to + timedelta(days=1),
                    month_end_exclusive,
                )

                if overlap_start >= overlap_end_exclusive:
                    continue

                from_dt = datetime.combine(
                    overlap_start,
                    datetime.min.time(),
                )

                to_dt = datetime.combine(
                    overlap_end_exclusive,
                    datetime.min.time(),
                )

                # Use this employee's working calendar
                days = employee.get_work_days_dashboard(
                    from_dt,
                    to_dt,
                )

                bucket['days'] += float(days or 0.0)

        clean_result = [
            {
                'month': bucket['month'],
                'days': round(bucket['days'], 2),
            }
            for bucket in result
        ]

        _logger.info(
            "[HRMS Dashboard] Monthly leave for employee %s: %s",
            employee.name,
            clean_result,
        )

        return clean_result

    def get_work_days_dashboard(self, from_datetime, to_datetime,
                                compute_leaves=False, calendar=None,
                                domain=None):
        """Calculate employee worked hours/day details"""
        resource = self.resource_id
        calendar = calendar or self.resource_calendar_id
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=utc)
        from_full = from_datetime - timedelta(days=1)
        to_full = to_datetime + timedelta(days=1)
        intervals = calendar._attendance_intervals_batch(from_full, to_full,
                                                         resource)
        day_total = defaultdict(float)
        for start, stop, meta in intervals[resource.id]:
            day_total[start.date()] += (stop - start).total_seconds() / 3600
        if compute_leaves:
            intervals = calendar._work_intervals_batch(from_datetime,
                                                       to_datetime, resource,
                                                       domain)
        else:
            intervals = calendar._attendance_intervals_batch(from_datetime,
                                                             to_datetime,
                                                             resource)
        day_hours = defaultdict(float)
        for start, stop, meta in intervals[resource.id]:
            day_hours[start.date()] += (stop - start).total_seconds() / 3600
        days = sum(
            float_utils.round(ROUNDING_FACTOR * day_hours[day] / day_total[
                day]) / ROUNDING_FACTOR
            for day in day_hours
        )
        return days


    @api.model
    def join_resign_trends(self):
        if self.check_user_has_employee():
            """Returns join/resign details of departments"""
            cr = self._cr
            month_list = []
            join_trend = []
            resign_trend = []
            for i in range(11, -1, -1):
                last_month = datetime.now() - relativedelta(months=i)
                text = format(last_month, '%B %Y')
                month_list.append(text)
            for month in month_list:
                vals = {
                    'l_month': month,
                    'count': 0
                }
                join_trend.append(vals)
            for month in month_list:
                vals = {
                    'l_month': month,
                    'count': 0
                }
                resign_trend.append(vals)
            cr.execute('''select to_char(joining_date, 'Month YYYY') as l_month,
             count(id) from hr_employee
            WHERE joining_date BETWEEN CURRENT_DATE - INTERVAL '12 months'
            AND CURRENT_DATE + interval '1 month - 1 day'
            group by l_month''')
            join_data = cr.fetchall()
            cr.execute('''select to_char(resign_date, 'Month YYYY') as l_month,
             count(id) from hr_employee
            WHERE resign_date BETWEEN CURRENT_DATE - INTERVAL '12 months'
            AND CURRENT_DATE + interval '1 month - 1 day'
            group by l_month;''')
            resign_data = cr.fetchall()

            for line in join_data:
                match = list(filter(
                    lambda d: d['l_month'].replace(' ', '') == line[0].replace(' ',
                                                                               ''),
                    join_trend))
                if match:
                    match[0]['count'] = line[1]
            for line in resign_data:
                match = list(filter(
                    lambda d: d['l_month'].replace(' ', '') == line[0].replace(' ',
                                                                               ''),
                    resign_trend))
                if match:
                    match[0]['count'] = line[1]
            for join in join_trend:
                join['l_month'] = join['l_month'].split(' ')[:1][0].strip()[:3]
            for resign in resign_trend:
                resign['l_month'] = resign['l_month'].split(' ')[:1][0].strip()[:3]
            graph_result = [{
                'name': 'Join',
                'values': join_trend
            }, {
                'name': 'Resign',
                'values': resign_trend
            }]
            return graph_result

    @api.model
    def get_attrition_rate(self):
        if self.check_user_has_employee():
            """Returns monthly wise attrition rate"""
            month_attrition = []
            monthly_join_resign = self.join_resign_trends()
            month_join = monthly_join_resign[0]['values']
            month_resign = monthly_join_resign[1]['values']
            sql = """
            SELECT (date_trunc('month', CURRENT_DATE))::date - interval '1' 
            month * s.a AS month_start
            FROM generate_series(0,11,1) AS s(a);"""
            self._cr.execute(sql)
            month_start_list = self._cr.fetchall()
            for month_date in month_start_list:
                self._cr.execute("""select count(id), 
                to_char(date '%s', 'Month YYYY') as l_month from hr_employee
                where resign_date> date '%s' or resign_date is null and 
                joining_date < date '%s'
                """ % (month_date[0], month_date[0], month_date[0],))
                month_emp = self._cr.fetchone()
                match_join = \
                    list(filter(
                        lambda d: d['l_month'] == month_emp[1].split(' ')[:1][
                                                      0].strip()[:3], month_join))[
                        0][
                        'count']
                match_resign = \
                    list(filter(
                        lambda d: d['l_month'] == month_emp[1].split(' ')[:1][
                                                      0].strip()[:3],
                        month_resign))[0][
                        'count']
                month_avg = (month_emp[0] + match_join - match_resign + month_emp[
                    0]) / 2
                attrition_rate = (match_resign / month_avg) * 100 \
                    if month_avg != 0 else 0
                vals = {
                    'month': month_emp[1].split(' ')[:1][0].strip()[:3],
                    'attrition_rate': round(float(attrition_rate), 2)
                }
                month_attrition.append(vals)
            return month_attrition

    @api.model
    def get_employee_skill(self):
        if not self.check_user_has_employee():
            return []

        employee = self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        if not employee:
            return []

        skills = self.env['hr.employee.skill'].sudo().search_read(
            [('employee_id', '=', employee.id)]
        )

        dataset = []
        for rec in skills:
            vals = {
                'skills': rec['skill_type_id'][1] + '-' + rec['skill_id'][1],
                'progress': rec['level_progress']
            }
            dataset.append(vals)

        return dataset