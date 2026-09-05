from odoo import _, http
from odoo.http import route, request
from odoo.addons.portal.controllers import portal
from werkzeug.utils import redirect
import base64


def get_activity_page_url(key, parent_student_param=None, id=None):
    if key == "list":
        return f"/student/activities/{parent_student_param}" if parent_student_param else f"/student/activities"
    elif key == "show":
        return f"/student/activity/{id}?parent_student_param={parent_student_param}" if parent_student_param else f"/student/activity/{id}"
    elif key == "home":
        return f"/my/home/{parent_student_param}" if parent_student_param else "/my/home"


class ActivityWebsite(portal.CustomerPortal):
    @route(
        ["/student/activities", "/student/activities/page/<int:page>", "/student/activities/<int:id>",
         "/student/activities/<int:id>/page/<int:page>"],
        auth="user",
        website=True,
    )
    def activities(self, date_begin=None, date_end=None, filterby=None, sortby='date_new', page=1,
                   **kwargs):
        parent_student_param = kwargs.get("id")

        domain = [('student_id', '=', parent_student_param)] if parent_student_param else []

        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        student_activity_env = request.env["de.activity"]

        searchbar_sorts = {
            'type_id': {'label': _('Activity type'), 'order': 'type_id'},
            'responsible_id': {'label': _('The Responsible'), 'order': 'responsible_id'},
            'date_new': {'label': _('Newest'), 'order': 'create_date DESC'},
            'date_old': {'label': _('Oldest'), 'order': 'create_date'},
            'state': {'label': _('State'), 'order': 'state'},
        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'accept': {'label': _('Accepted'), 'domain': [('state', '=', 'accept')]},
            'reject': {'label': _('Rejected'), 'domain': [('state', '=', 'reject')]},
        }

        if not sortby:
            sortby = 'date_new'
        order = searchbar_sorts[sortby]['order']
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # Prepare pager data
        student_activity_count = student_activity_env.search_count(domain)
        page_url = f"/student/activities/{parent_student_param}" if parent_student_param else "/student/activities"
        pager_data = portal.pager(
            url=page_url,
            total=student_activity_count,
            page=page,
            step=self._items_per_page,
            url_args={'date_begin': date_begin,
                      'date_end': date_end, 'sortby': sortby,
                      'filterby': filterby, }
        )
        # Recordset according to pager and domain filter
        student_activity = student_activity_env.search(
            domain, order=order, limit=self._items_per_page, offset=pager_data["offset"]
        )
        # Prepare template values
        values = self._prepare_portal_layout_values()

        values.update(
            {
                "activity_records": student_activity,
                "page_name": "Activities",
                "default_url": page_url,
                "page_url": page_url,
                "pager": pager_data,
                'date': date_begin,
                'date_end': date_end,
                "home_url": get_activity_page_url('home', parent_student_param),
                'searchbar_sortings': searchbar_sorts,
                'sortby': sortby,
                'filterby': filterby,
                'searchbar_filters': searchbar_filters,
                'parent_student_param': parent_student_param,
                'student': helper.get_student(parent_student_param)
            }
        )
        return request.render("dekad_activity.student_activity", values)

    @route("/student/activity/<model('de.activity'):record>", auth='user', website=True)
    def activity_show(self, record, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')

        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        model_attachment = {
            "model": "de.activity",
            "field": "file",
            "id": record.id,
        }
        data_object = helper.get_file_attachment_type(model_attachment)
        file_name = record.file_name
        # file_type = data_object['file_type']

        return http.request.render('dekad_activity.student_activity_show', {
            'page_name': 'Activity show',
            "home_url": get_activity_page_url('home', parent_student_param),
            "list_url": get_activity_page_url('list', parent_student_param),
            "page_url": get_activity_page_url('show', parent_student_param, record.id),
            "record": record,
            'parent_student_param': parent_student_param,
            'student': helper.get_student(parent_student_param),
            'file_name': f"{file_name}" if data_object[
                'attachment'] else "",
        })

    @route("/student/activity/<model('de.activity'):record>/accept", auth='user', website=True)
    def activity_accept(self, record, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')
        record.write({'state': 'accept'})
        return redirect(f"/student/activities/{parent_student_param}")

    @route("/student/activity/<model('de.activity'):record>/reject", auth='user', website=True)
    def activity_reject(self, record, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')
        record.write({'state': 'reject'})
        return redirect(f"/student/activities/{parent_student_param}")

    @route('/student/activity/download/<model("de.activity"):record>', type='http',
           auth="user")
    def activity_download(self, record):
        data_object = {
            'model': 'de.activity',
            'field': 'file',
            'id': record.id
        }
        file_object = helper.get_file_attachment_type(data_object)

        pdf_file = base64.b64decode(record.file)

        headers = [
            ('Content-Type', file_object["attachment"].mimetype),
            ('Content-Disposition',
             f'attachment; filename="activity - {record.file_name}"')
        ]

        return request.make_response(pdf_file, headers=headers)

