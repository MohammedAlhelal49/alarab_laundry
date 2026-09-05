from odoo import _
from odoo.http import route, request
from odoo.addons.portal.controllers import portal
from werkzeug.utils import redirect
from odoo.exceptions import AccessError


class AttendanceWebsite(portal.CustomerPortal):

    @route(
        ["/student/attendance", "/student/attendance/page/<int:page>", "/student/attendance/<int:id>",
         "/student/attendance/<int:id>/page/<int:page>"],
        auth="user",
        website=True,
    )
    def attendance(self, date_begin=None, date_end=None, filterby=None, sortby='date_new', page=1, **kwargs):
        parent_student_param = kwargs.get("id")
        user = request.env.user

        # SECURITY: Check if parent has access to this specific student
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # Redirect check
        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        # Define domain based on user type and access permissions
        if parent_student_param:
            # Parent viewing specific student's attendance
            domain = [('student_id', '=', int(parent_student_param))]
            use_sudo = True  # Parents need sudo access to view attendance records
        else:
            # Student viewing their own attendance
            current_student = request.env['de.student'].search([('user_id', '=', user.id)])
            if current_student:
                domain = [('student_id', '=', current_student.id)]
                use_sudo = False  # Students can access their own records directly
            else:
                domain = [('id', '=', False)]  # No records if student not found
                use_sudo = False

        print(f"User: {user.name}, is_parent: {getattr(user, 'is_parent', False)}")
        print(f"Parent student param: {parent_student_param}")
        print(f"Domain: {domain}")
        print(f"Use sudo: {use_sudo}")

        student_attendance_env = request.env["de.attendance.line"]
        if use_sudo:
            student_attendance_env = student_attendance_env.sudo()

        searchbar_sorts = {
            'date_new': {'label': _('Newest'), 'order': 'attendance_date DESC'},
            'date_old': {'label': _('Oldest'), 'order': 'attendance_date'},
            'present': {'label': _('Present'), 'order': 'present desc'},
            'absent': {'label': _('Absent'), 'order': 'absent desc'},
            'leave': {'label': _('Leave'), 'order': 'leave desc'},
        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'Present': {'label': _('Present'), 'domain': [('present', '=', True)]},
            'absent': {'label': _('Absent'), 'domain': [('absent', '=', True)]},
            'leave': {'label': _('Leave'), 'domain': [('leave', '=', True)]},
        }

        # Apply sorting and filtering
        if not sortby:
            sortby = 'date_new'
        order = searchbar_sorts[sortby]['order']

        if not filterby:
            filterby = 'all'

        # Combine base domain with filter domain
        final_domain = domain + searchbar_filters[filterby]['domain']
        print(f"Final domain: {final_domain}")

        # Get count and records with proper permissions
        student_attendance_count = student_attendance_env.search_count(final_domain)
        print(f"Attendance count: {student_attendance_count}")

        # Prepare pager data
        page_url = f"/student/attendance/{parent_student_param}" if parent_student_param else "/student/attendance"
        pager_data = portal.pager(
            url=page_url,
            total=student_attendance_count,
            page=page,
            step=self._items_per_page,
            url_args={
                'date_begin': date_begin,
                'date_end': date_end,
                'sortby': sortby,
                'filterby': filterby
            }
        )

        # Get attendance records with proper permissions
        student_attendance = student_attendance_env.search(
            final_domain,
            order=order,
            limit=self._items_per_page,
            offset=pager_data["offset"]
        )

        print(f"Found attendance records: {len(student_attendance)}")

        # Prepare template values
        values = self._prepare_portal_layout_values()
        values.update({
            "attendance_records": student_attendance,
            "page_name": "Attendance",
            "default_url": page_url,
            "pager": pager_data,
            'date': date_begin,
            'date_end': date_end,
            'searchbar_sortings': searchbar_sorts,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            "page_url": page_url,
            "home_url": f"/my/home/{parent_student_param}" if parent_student_param else "/my/home",
            "parent_student_param": parent_student_param,
            'student': helper.get_student(parent_student_param)
        })

        return request.render("dekad_attendance.student_attendance", values)