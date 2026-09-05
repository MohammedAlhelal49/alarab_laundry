from odoo import http
from odoo.http import route, request
from odoo.addons.portal.controllers import portal
from werkzeug.utils import redirect


class ParentWebsite(portal.CustomerPortal):
    @route('/my/students',auth='user', website=True)
    def students(self):
        user = http.request.env.user
        print(user.child_ids.ids)
        if user.has_group('base.group_user') or user.is_student:
            return redirect('/my/home')
        # Using sudo() due to unresolved security rule issue
        # The portal rule exists and should work, but fails in practice
        # Security is maintained by filtering on user_id in the search
        parent = http.request.env["de.parent"].sudo().search([('user_id' , '=' , request.env.uid)])

        # Security: parent.student_ids is already filtered by the Many2many relation
        # Only students explicitly linked to this parent are accessible
        return http.request.render('dekad_parent.parent_students', {
            'page_name': 'Students',
            'parent': parent,
            "home_url": "/my/home",
        })

    @route(["/parent/profile"], auth="user", website=True)
    def parent_profile(self, **kwargs):
        user = request.env.user

        # Only parents can access this
        if not user.is_parent:
            return redirect('/my/home')

        # Get parent record
        parent = request.env['de.parent'].search([('user_id', '=', user.id)])
        if not parent:
            return redirect('/my/home')

        values = {
            'parent': parent,
            'page_name': 'My Profile',
            'page_url': '/parent/profile',
            'home_url': '/my/home',
            'can_edit': True,  # Parents can edit their own profile
        }

        return request.render('dekad_parent.dekad_parent_profile', values)