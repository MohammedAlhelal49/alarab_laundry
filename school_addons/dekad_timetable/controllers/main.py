from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from collections import defaultdict
from werkzeug.utils import redirect


class TimetablePortalController(CustomerPortal):

    @http.route([
        '/student/timetable',
        '/student/timetable/<int:id>'
    ], type='http', auth='user', website=True)
    def student_timetable(self, id=None, **kwargs):
        """Display student's timetable"""
        parent_student_param = id

        # Security check using existing helper
        if helper.redirect_portal_page(parent_student_param, False):
            return redirect(helper.redirect_portal_page(parent_student_param, False))

        # Additional parent security check
        if request.env.user.is_parent and parent_student_param:
            if not helper.check_parent_student(parent_student_param):
                return redirect('/my/students')

        # Get student record using existing helper (uses sudo internally)
        student = helper.get_student(parent_student_param)

        if not student:
            return redirect('/my')

        # Get current timetable - use sudo() since controller handles security
        timetable = request.env['de.timetable'].sudo().search([
            ('grade_id', '=', student.grade.id),
            ('classroom_id', '=', student.classroom_id.id)
        ], limit=1, order='create_date desc')

        # Get all periods - use sudo() as periods are shared/global data
        periods = request.env['de.period'].sudo().search([], order='start_time')

        # Get days of week - FIXED: Use actual selection values
        days = [
            ('mon', 'Monday'),
            ('tue', 'Tuesday'),
            ('wed', 'Wednesday'),
            ('thu', 'Thursday'),
            ('fri', 'Friday'),
            ('sat', 'Saturday'),
            ('sun', 'Sunday'),
        ]

        # Organize timetable data in a grid structure
        timetable_grid = defaultdict(dict)

        if timetable:
            for line in timetable.line_ids:
                if line.session_slot_id and line.session_slot_id.period_id:
                    day = line.session_slot_id.day_of_week
                    period = line.session_slot_id.period_id
                    timetable_grid[day][period.id] = {
                        'subject': line.subject_id.name if line.subject_id else '',
                        'teacher': line.teacher_id.name if line.teacher_id else '',
                        'is_break': period.is_break,
                    }

        # Home URL using your pattern
        home_url = f'/my/home/{parent_student_param}' if parent_student_param else '/my/home'

        values = {
            'student': student,
            'timetable': timetable,
            'periods': periods,
            'days': days,
            'timetable_grid': dict(timetable_grid),
            'page_name': 'Timetable',
            'parent_student_param': parent_student_param,
            'home_url': home_url,
        }

        return request.render('dekad_timetable.student_timetable_portal', values)

    @http.route(['/my/timetable/<int:timetable_id>/pdf'], type='http', auth='user', website=True)
    def download_timetable_pdf(self, timetable_id, **kwargs):
        """Download timetable as PDF"""
        # Get the timetable
        timetable = request.env['de.timetable'].sudo().browse(timetable_id)

        if not timetable.exists():
            return redirect('/my')

        # Security check - verify user has access to this timetable
        user = request.env.user

        if user.is_student:
            # Students can only download their own classroom's timetable
            student = request.env['de.student'].search([('user_id', '=', user.id)], limit=1)
            if not student or timetable.grade_id.id != student.grade.id or timetable.classroom_id.id != student.classroom_id.id:
                return redirect('/my')

        elif user.is_parent:
            # Parents can download their children's classroom timetables
            parent = request.env['de.parent'].sudo().search([('user_id', '=', user.id)], limit=1)
            if not parent:
                return redirect('/my')

            # Check if any child is in this grade/classroom
            children_grades = parent.student_ids.mapped('grade.id')
            children_classrooms = parent.student_ids.mapped('classroom_id.id')

            if timetable.grade_id.id not in children_grades or timetable.classroom_id.id not in children_classrooms:
                return redirect('/my/students')
        else:
            return redirect('/my')

        # Generate and return PDF using existing report
        report = request.env.ref('dekad_timetable.action_report_timetable_pdf').sudo()
        pdf_content, _ = report.sudo()._render_qweb_pdf(report.report_name, res_ids=timetable.ids)

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', 'attachment; filename="Timetable_%s.pdf"' % timetable.name.replace(' ', '_'))
        ]

        return request.make_response(pdf_content, headers=pdfhttpheaders)