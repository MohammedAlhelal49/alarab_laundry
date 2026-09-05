from odoo.http import route, request
from odoo.addons.portal.controllers import portal
from werkzeug.utils import redirect
import magic, base64
from odoo import http, _


class HealthWebsite(portal.CustomerPortal):

    @route(
        ["/student/health", "/student/health/page/<int:page>", "/student/health/<int:id>",
         "/student/health/<int:id>/page/<int:page>"],
        auth="user",
        website=True,
    )
    def health(self, date_begin=None, date_end=None, sortby='date_new', page=1, filterby=None, search='',
               search_in='name', **kwargs):
        parent_student_param = kwargs.get("id")
        domain = [('student_id', '=', parent_student_param)] if parent_student_param else []

        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        student_health_env = request.env["de.health.checkup"]
        searchbar_sorts = {
            'date_new': {'label': _('Newest'), 'order': 'create_date desc'},
            'date_old': {'label': _('Oldesr'), 'order': 'create_date'},
        }
        if not sortby:
            sortby = 'date_new'
        order = searchbar_sorts[sortby]['order']

        search_list = {
            'name': {'label': _('Name'), 'input': 'name', 'domain': [('name', 'ilike', search)]}
        }
        search_domain = search_list[search_in]['domain']

        if not search_in:
            search_in = 'name'
        if search and search_in:
            domain += search_domain

        # Prepare pager data
        student_health_count = student_health_env.search_count(domain)
        page_url = f"/student/health/{parent_student_param}" if parent_student_param else "/student/health"
        pager_data = portal.pager(
            url=page_url,
            total=student_health_count,
            page=page,
            step=self._items_per_page,
            url_args={'date_begin': date_begin, 'filterby': filterby,
                      'date_end': date_end, 'sortby': sortby, 'search': search, 'search_in': search_in}
        )
        # Recordset according to pager and domain filter
        student_health = student_health_env.search(
            domain, order=order, limit=self._items_per_page, offset=pager_data["offset"]
        )
        # Prepare template values
        values = self._prepare_portal_layout_values()
        health = request.env["de.health"].search(
            [('student_id', '=', parent_student_param)]) if parent_student_param else request.env["de.health"].search(
            [('student_id', '=', helper.get_student(parent_student_param).id)])
        values.update(
            {
                'health': health,
                "health_records": student_health,
                "default_url": page_url,
                "page_url": page_url,
                "pager": pager_data,
                'date': date_begin,
                'date_end': date_end,
                'searchbar_sortings': searchbar_sorts,
                'sortby': sortby,
                'search': search,
                'search_in': search_in,
                'searchbar_inputs': search_list,
                'filterby': filterby,
                "page_name": "Health",
                "home_url": f"/my/home/{parent_student_param}" if parent_student_param else "/my/home",
                "parent_student_param": parent_student_param,
                'student': helper.get_student(parent_student_param)
            }
        )
        return request.render("dekad_health.student_health", values)

    @route('/student/checkup/download/<model("de.health.checkup"):checkup>', type='http',
           auth="user")
    def download_checkup_image(self, checkup):
        data_object = {
            'model': 'de.health.checkup',
            'field': 'file',
            'id': checkup.id

        }
        file_object = helper.get_file_attachment_type(data_object)

        pdf_file = base64.b64decode(checkup.file)
        headers = [
            ('Content-Type', file_object["attachment"].mimetype),
            ('Content-Disposition', f'attachment; filename="{checkup.name}-{checkup.file_name}"')
        ]
        return request.make_response(pdf_file, headers=headers)

    @route("/student/health_rec/<model('de.health.checkup'):record>", auth='user', website=True)
    def checkup_show(self, record, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')
        print(parent_student_param)

        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        model_attachment = {
            "model": "de.health.checkup",
            "field": "file",
            "id": record.id,
        }
        data_object = helper.get_file_attachment_type(model_attachment)
        # file_name = record.name
        # file_type = data_object['file_type']

        return http.request.render('dekad_health.student_health_show', {
            'page_name': 'Health Show',
            "home_url": f"/my/home/{parent_student_param}" if parent_student_param else "/my/home",
            "list_url": f"/student/health/{parent_student_param}" if parent_student_param else "/student/health",
            "page_url": f"/student/health_rec/{record.id}?parent_student_param={parent_student_param}" if parent_student_param else f"/student/health_rec/{record.id}",
            "record": record,
            'parent_student_param': parent_student_param,
            'student': helper.get_student(parent_student_param),
            'file_name': f"{record.file_name}" if data_object[
                'attachment'] else "",
        })
