from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal
from werkzeug.utils import redirect
from odoo import http


class CustomerPortalInherited(CustomerPortal):

    @route(['/my', '/my/home', '/my/<int:id>', '/my/home/<int:id>'], type='http', auth="user", website=True)
    def home(self, **kw):
        if not request.env.user.share:
            return redirect('/web')

        parent_student_param = kw.get("id")
        user = request.env.user

        # CRITICAL SECURITY CHECK: Verify parent access to student
        if user.is_parent and parent_student_param:
            parent_record = request.env['de.parent'].sudo().search([('user_id', '=', user.id)])
            print(parent_record.student_ids.ids)
            if not parent_record or int(parent_student_param) not in parent_record.student_ids.ids:
                # Unauthorized access attempt - log and redirect
                request.session['error_message'] = 'Access denied: You can only view your own children\'s information.'
                return redirect('/my/students')

        # Check other redirect conditions
        if helper.redirect_portal_page(parent_student_param, True):
            return redirect(helper.redirect_portal_page(parent_student_param, True))

        values = self._prepare_portal_layout_values()

        if request.env.user.has_group('base.group_portal'):
            # Prepare all document access with proper security
            values["student_profile_document"] = helper.access_customer_document("profile", parent_student_param)
            values["student_fee_document"] = helper.access_customer_document("fee", parent_student_param)
            values["student_health_document"] = helper.access_customer_document("health", parent_student_param)
            values["student_complaint_document"] = helper.access_customer_document("complaint", parent_student_param)
            values["student_note_document"] = helper.access_customer_document("note", parent_student_param)
            values["student_contravention_document"] = helper.access_customer_document("contravention",
                                                                                       parent_student_param)
            values["student_attendance_document"] = helper.access_customer_document("attendance", parent_student_param)
            values["student_achievement_document"] = helper.access_customer_document("achievement",
                                                                                     parent_student_param)
            values["student_activity_document"] = helper.access_customer_document("activity", parent_student_param)
            values["student_assignment_document"] = helper.access_customer_document("assignment", parent_student_param)
            values["student_quiz_document"] = helper.access_customer_document("quiz", parent_student_param)
            values["student_leave_document"] = helper.access_customer_document("leave", parent_student_param)
            values["student_timetable_document"] = helper.access_customer_document("timetable", parent_student_param)

            values["parent_student_param"] = parent_student_param
            # THIS for parent's own profile
            if request.env.user.is_parent and not parent_student_param:
                values["parent_profile_document"] = helper.access_customer_document("parent_profile", None)
            print("******************")
            print(values)
            print('***********')
            # Safe student data access with proper error handling
            if parent_student_param:
                try:
                    student = request.env['de.student'].sudo().browse(int(parent_student_param))
                    if student.exists():
                        values["student"] = student
                        values["student_name"] = student.name
                        values["student_grade"] = student.grade.name if student.grade else "Not assigned"
                    else:
                        values["student"] = False
                        values["student_name"] = "Student not found"
                        values["student_grade"] = ""
                except Exception as e:
                    values["student"] = False
                    values["student_name"] = "Error loading student"
                    values["student_grade"] = ""
            else:
                # Student accessing their own data
                student = request.env['de.student'].search([('user_id', '=', request.env.user.id)])
                values["student"] = student
                values["student_name"] = student.name if student else ""
                values["student_grade"] = student.grade.name if student and student.grade else ""

            values["is_customer_document_page"] = True
            values["parent"] = request.env['de.parent'].sudo().search([('user_id', '=', request.env.user.id)])

            # Parent page counts (only for parents)
            if user.is_parent:
                parent_record = request.env['de.parent'].sudo().search([('user_id', '=', request.env.user.id)])
                if parent_record:
                    values["parent_note_document_count"] = request.env['de.note'].search_count([
                        '|', ('group_id.all_parents', '=', True),
                        ('group_id.parent_ids.id', '=', parent_record.id)
                    ])
                    values["parent_complaint_document_count"] = request.env['de.complaint'].sudo().search_count([
                        ('parent_id', '=', parent_record.id)
                    ])

        return request.render("dekad_web.dekad_portal_my_home", values)