from odoo import http
from odoo.http import route, request
from odoo.addons.portal.controllers import portal
from werkzeug.utils import redirect

class CoreWebsite(portal.CustomerPortal):

    @route(
        ["/student/profile", "/student/profile/<int:id>"],
        auth="user",
        website=True,
    )
    def profile(self, **kw):
        parent_student_param = kw.get("id")
        student_domain = [('id', '=', parent_student_param)] if parent_student_param else []
        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))
        student = request.env['de.student'].sudo().search(student_domain)
        print(student)
        data_object = {
            'model': 'de.student',
            'record': student,
            'field': 'gender'
        }
        values = {'student': student, 'student_gender': helper.get_selection_label(data_object),
                  'page_name': 'Profile',
                  'page_url': "/student/profile" if not parent_student_param else f"/student/profile/{str(parent_student_param)}",
                  "home_url": f"/my/home/{parent_student_param}" if parent_student_param else "/my/home",
                  "parent_student_param": parent_student_param,
                  'student': helper.get_student(parent_student_param)
                  }
        for key, value in values.items():
            print(f"Key: {key}, Value: {value}")

        return http.request.render('dekad_core.student_profile', values)
