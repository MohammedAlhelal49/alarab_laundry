from odoo import _, http
from odoo.http import route, request
from odoo.addons.portal.controllers import portal
from werkzeug.utils import redirect
import base64


def get_contravention_page_url(key, parent_student_param=None, id=None):
    if key == "list":
        return f"/student/contraventions/{parent_student_param}" if parent_student_param else f"/student/contraventions"
    elif key == "show":
        return f"/student/contravention/{id}?parent_student_param={parent_student_param}" if parent_student_param else f"/student/contravention/{id}"
    elif key == "home":
        return f"/my/home/{parent_student_param}" if parent_student_param else "/my/home"


class ContraventionWebsite(portal.CustomerPortal):
    @route(
        ["/student/contraventions", "/student/contraventions/page/<int:page>", "/student/contraventions/<int:id>",
         "/student/contraventions/<int:id>/page/<int:page>"],
        auth="user",
        website=True,
    )
    def contraventions(self, date_begin=None, date_end=None, filterby=None, sortby='date_new', page=1,
                       **kwargs):
        parent_student_param = kwargs.get("id")

        domain = [('student_id', '=', parent_student_param)] if parent_student_param else []

        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        student_contravention_env = request.env["de.contravention"]

        searchbar_sorts = {
            'priority': {'label': _('Priority'), 'order': 'priority'},
            'date_new': {'label': _('Newest'), 'order': 'create_date DESC'},
            'date_old': {'label': _('Oldest'), 'order': 'create_date'},
            'category': {'label': _('Category'), 'order': 'category_id '},
            'state': {'label': _('State'), 'order': 'state'},

        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'penalty': {'label': _('Penalty'), 'domain': [('penalty_ids', '!=', False)]},
            'suspend': {'label': _('Suspend'), 'domain': [('suspend_ids', '!=', False)]},
        }

        if not sortby:
            sortby = 'date_new'
        order = searchbar_sorts[sortby]['order']
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # Prepare pager data
        student_contravention_count = student_contravention_env.search_count(domain)
        page_url = f"/student/contraventions/{parent_student_param}" if parent_student_param else "/student/contraventions"
        pager_data = portal.pager(
            url=page_url,
            total=student_contravention_count,
            page=page,
            step=self._items_per_page,
            url_args={'date_begin': date_begin,
                      'date_end': date_end, 'sortby': sortby,
                      'filterby': filterby, }
        )
        # Recordset according to pager and domain filter
        student_contravention = student_contravention_env.search(
            domain, order=order, limit=self._items_per_page, offset=pager_data["offset"]
        )
        # Prepare template values
        values = self._prepare_portal_layout_values()

        values.update(
            {
                "contravention_records": student_contravention,
                "page_name": "Contraventions",
                "default_url": page_url,
                "page_url": page_url,
                "pager": pager_data,
                'date': date_begin,
                'date_end': date_end,
                "home_url": get_contravention_page_url('home', parent_student_param),
                'searchbar_sortings': searchbar_sorts,
                'sortby': sortby,
                'searchbar_filters': searchbar_filters,
                'filterby': filterby,
                'parent_student_param': parent_student_param,
                'student': helper.get_student(parent_student_param)
            }
        )
        return request.render("dekad_contravention.student_contravention", values)

    @route("/student/contravention/<model('de.contravention'):record>", auth='user', website=True)
    def contravention_show(self, record, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')

        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        model_attachment = {
            "model": "de.contravention",
            "field": "file",
            "id": record.id,
        }
        data_object = helper.get_file_attachment_type(model_attachment)
        file_name = record.file_name
        # file_type = data_object['file_type']

        return http.request.render('dekad_contravention.student_contravention_show', {
            'page_name': 'Contravention show',
            "home_url": get_contravention_page_url('home', parent_student_param),
            "list_url": get_contravention_page_url('list', parent_student_param),
            "page_url": get_contravention_page_url('show', parent_student_param, record.id),
            "record": record,
            'parent_student_param': parent_student_param,
            'student': helper.get_student(parent_student_param),
            'file_name': f"{file_name}" if data_object[
                'attachment'] else "",
        })

    @route('/student/contravention/download/<model("de.contravention"):record>', type='http',
           auth="user")
    def contravention_download(self, record):
        data_object = {
            'model': 'de.contravention',
            'field': 'file',
            'id': record.id
        }
        file_object = helper.get_file_attachment_type(data_object)

        pdf_file = base64.b64decode(record.file)

        headers = [
            ('Content-Type', file_object["attachment"].mimetype),
            ('Content-Disposition',
             f'attachment; filename="contravention - .{record.file_name}"')
        ]

        return request.make_response(pdf_file, headers=headers)

# Contravention Show