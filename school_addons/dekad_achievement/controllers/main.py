from odoo import _
from odoo.http import route, request
from odoo.addons.portal.controllers import portal
from werkzeug.utils import redirect


class AchievementWebsite(portal.CustomerPortal):

    @route(
        ["/student/achievements", "/student/achievements/page/<int:page>", "/student/achievements/<int:id>",
         "/student/achievements/<int:id>/page/<int:page>"],
        auth="user",
        website=True,
    )
    def achievements(self, date_begin=None, date_end=None, filterby=None, sortby='date_new', page=1, **kwargs):
        parent_student_param = kwargs.get("id")
        domain = [('student_id', '=', parent_student_param)] if parent_student_param else []
        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))
        student_achievement_env = request.env["de.student.achievement.assign"]

        # Prepare pager data
        student_achievement_count = student_achievement_env.search_count(domain)
        page_url = f"/student/achievements/{parent_student_param}" if parent_student_param else "/student/achievements"
        # Recordset according to pager and domain filter
        student_achievement = student_achievement_env.search(domain)

        # Prepare template values
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "achievement_records": student_achievement,
                "page_name": "Achievements",
                "default_url": page_url,
                "page_url": page_url,
                "home_url": f"/my/home/{parent_student_param}" if parent_student_param else "/my/home",
                "parent_student_param": parent_student_param,
                'student': helper.get_student(parent_student_param)
            }
        )
        return request.render("dekad_achievement.student_achievement", values)
