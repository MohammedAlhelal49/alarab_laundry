from odoo import http, _
from odoo.http import route, request, Response
from odoo.addons.portal.controllers import portal
import base64, json
from werkzeug.utils import redirect
from datetime import datetime
from odoo.exceptions import AccessError, ValidationError



def get_leave_page_url(key, parent_student_param=None, id=None):
    if key == "list":
        return f"/student/leaves/{parent_student_param}" if parent_student_param else "/student/leaves"
    elif key == "show":
        return f"/student/leave/{id}?parent_student_param={parent_student_param}" if parent_student_param else f"/student/leave/{id}"
    elif key == "home":
        return f"/my/home/{parent_student_param}" if parent_student_param else "/my/home"
    elif key == "create":
        return f"/student/leave/create?parent_student_param={parent_student_param}" if parent_student_param else "/student/leave/create"
    elif key == "update":
        return f"/student/leave/update/{id}?parent_student_param={parent_student_param}" if parent_student_param else f"/student/leave/update/{id}"


class LeaveWebsite(portal.CustomerPortal):

    @route(
        ["/student/leaves", "/student/leaves/<int:id>", "/student/leaves/<int:id>/page/<int:page>",
         "/student/leaves/page/<int:page>"],
        auth="user",
        website=True,
    )
    def leaves(self, date_begin=None, date_end=None, filterby=None, sortby='date_new', page=1,
               **kwargs):
        success_message = request.session.get('success_message')
        request.session['success_message'] = ''
        parent_student_param = kwargs.get("id")
        domain = [('student_id', '=', parent_student_param)] if parent_student_param else []
        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))
        student_leave_env = request.env["de.leave"]

        searchbar_sorts = {
            'date_new': {'label': _('Newest'), 'order': 'start_date DESC'},
            'date_old': {'label': _('Oldest'), 'order': 'start_date'},
            'type': {'label': _('Leave Type'), 'order': 'leave_type'},
            'state': {'label': _('State'), 'order': 'state'},
        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'sent': {'label': _('Sent'), 'domain': [('state', '=', 'confirm')]},
            'accept': {'label': _('Accepted'), 'domain': [('state', '=', 'accept')]},
            'reject': {'label': _('Rejected'), 'domain': [('state', '=', 'reject')]},
            'start': {'label': _('Started'), 'domain': [('state', '=', 'start')]},
            'finished': {'label': _('Finished'), 'domain': [('state', '=', 'finish')]},
        }

        if not sortby:
            sortby = 'date_new'
        order = searchbar_sorts[sortby]['order']
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        # Prepare pager data
        student_leave_count = student_leave_env.search_count(domain)
        page_url = get_leave_page_url('list', parent_student_param)
        pager_data = portal.pager(
            url=page_url,
            total=student_leave_count,
            page=page,
            step=self._items_per_page,
            url_args={'date_begin': date_begin,
                      'date_end': date_end, 'sortby': sortby,
                      'filterby': filterby, }
        )
        # Recordset according to pager and domain filter
        student_leave = student_leave_env.search(
            domain, order=order, limit=self._items_per_page, offset=pager_data["offset"]
        )

        # Prepare template values
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "Leaves",
                "create_url": get_leave_page_url('create', parent_student_param),
                "page_url": page_url,
                "home_url": get_leave_page_url('home', parent_student_param),
                "leave_records": student_leave,
                "default_url": page_url,
                "pager": pager_data,
                'date': date_begin,
                'date_end': date_end,
                'searchbar_sortings': searchbar_sorts,
                'sortby': sortby,
                'searchbar_filters': searchbar_filters,
                'filterby': filterby,
                "parent_student_param": parent_student_param,
                "success_message": success_message or "",
                'student': helper.get_student(parent_student_param)
            }

        )
        return request.render("dekad_leave.student_leave", values)

    @route('/student/leave/delete/<model("de.leave"):record>', auth='user',
           website=True)
    def leave_delete(self, record, **kwargs):
        parent_student_param = int(kwargs.get('parent_student_param')) if kwargs.get('parent_student_param') else None
        record.unlink() if record.exists() else None
        request.session['success_message'] = 'Day off deleted'
        return redirect(
            get_leave_page_url('list', parent_student_param=parent_student_param))

    @route('/student/leave/download/<model("de.leave"):record>', type='http',
           auth="user")
    def leave_download(self, record):
        data_object = {
            'model': 'de.leave',
            'field': 'file',
            'id': record.id
        }
        file_object = helper.get_file_attachment_type(data_object)

        pdf_file = base64.b64decode(record.file)

        headers = [
            ('Content-Type', file_object["attachment"].mimetype),
            ('Content-Disposition',
             f'attachment; filename="{record.student_id.name} - day off- {record.file_name}"')
        ]

        return request.make_response(pdf_file, headers=headers)

    @route("/student/leave/<model('de.leave'):record>", auth='user', website=True)
    def leave_show(self, record, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')
        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))
        model_attachment = {
            "model": "de.leave",
            "field": "file",
            "id": record.id,
        }
        data_object = helper.get_file_attachment_type(model_attachment)
        file_name = f"{record.student_id.name} leave"
        # file_name = record.name_get()[0][1]
        file_type = data_object['file_type']
        return http.request.render('dekad_leave.student_leave_show', {
            'page_name': 'Leave Show',
            "home_url": get_leave_page_url('home', parent_student_param),
            "list_url": get_leave_page_url('list', parent_student_param),
            "page_url": get_leave_page_url('show', parent_student_param, record.id),
            "record": record,
            "parent_student_param": parent_student_param,
            'student': helper.get_student(parent_student_param),
            'file_name': f"{file_name}-{record.file_name}" if data_object[
                'attachment'] else "",
        })

    @route("/student/leave/create", auth='user', website=True)
    def leave_create_form(self, **kwargs):
        parent_student_param = int(kwargs.get('parent_student_param')) if kwargs.get('parent_student_param') else None

        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        leave_types = request.env['de.leave.type'].search([])
        return http.request.render('dekad_leave.student_leave_create', {
            'page_name': 'Leave Create',
            "home_url": get_leave_page_url('home', parent_student_param),
            "page_url": get_leave_page_url('create', parent_student_param),
            "leave_types": leave_types,
            'student_id': helper.get_student_id(parent_student_param),
            "parent_student_param": parent_student_param,
            'student': helper.get_student(parent_student_param),
            'list_url': get_leave_page_url('list', parent_student_param)
        })

    @route('/student/leave/create', auth='user', website=True, methods=['POST'])
    def leave_create(self, **kwargs):
        start_date = kwargs.get('start_date')  # Already in YYYY-MM-DD format
        end_date = kwargs.get('end_date')
        parent_student_param = kwargs.get('parent_student_param')
        data_object = {}
        # file = kwargs.get('file').read() if kwargs.get('file') else False
        # Process uploaded file using helper function
        file_data = helper.process_uploaded_file(kwargs.get('file'), max_size_mb=2)

        if file_data['error']:
            # Handle error (you might want to show this in the form)
            raise ValidationError(file_data['error'])

        # Add file data if uploaded
        if file_data['file_content']:
            data_object['file'] = file_data['file_content']
            data_object['file_name'] = file_data['filename']

        # data_object['file'] = base64.b64encode(file_data) if file and helper.get_file_size(
        #     kwargs.get('file')) < 2000000 else False
        data_object['student_id'] = int(kwargs.get('student_id'))
        data_object['description'] = kwargs.get('description')
        data_object['leave_type'] = int(kwargs.get('leave_type'))
        data_object['start_date'] = start_date
        data_object['end_date'] = end_date
        data_object['state'] = 'confirm'
        request.env["de.leave"].create(data_object)
        request.session['success_message'] = 'Day off created'

        return redirect(
            get_leave_page_url('list', parent_student_param=parent_student_param))

    @route("/student/leave/update/<model('de.leave'):record>", auth='user', website=True)
    def leave_update_form(self, record, **kwargs):
        parent_student_param = int(kwargs.get('parent_student_param')) if kwargs.get('parent_student_param') else None
        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        model_attachment = {
            "model": "de.leave",
            "field": "file",
            "id": record.id,
        }
        data_object = helper.get_file_attachment_type(model_attachment)

        # file_name = f"{record.student_id.name} leave"
        file_name = record.file_name

        file_type = data_object['file_type']

        leave_types = request.env['de.leave.type'].search([])

        return http.request.render('dekad_leave.student_leave_update', {
            'page_name': 'Leave Update',
            "home_url": get_leave_page_url('home', parent_student_param),
            "page_url": get_leave_page_url('update', parent_student_param, record.id),
            "show_url": get_leave_page_url('show', parent_student_param, record.id),
            "leave_types": leave_types,
            "record": record,
            'student_id': helper.get_student_id(parent_student_param),
            "parent_student_param": parent_student_param,
            'student': helper.get_student(parent_student_param),
            'list_url': get_leave_page_url('list', parent_student_param),
            'file_name': f"{file_name}.{file_type}" if data_object[
                'attachment'] else "",
        })

    @route('/student/leave/update', type='http', website=True, auth='user', methods=['POST'])
    def leave_update(self, **kwargs):
        start_date = kwargs.get('start_date')  # Already in YYYY-MM-DD format
        end_date = kwargs.get('end_date')

        parent_student_param = kwargs.get('parent_student_param')
        data_object = {}
        data_object = {}
        # file = kwargs.get('file').read() if kwargs.get('file') else False
        # Process uploaded file using helper function
        file_data = helper.process_uploaded_file(kwargs.get('file'), max_size_mb=2)

        if file_data['error']:
            # Handle error (you might want to show this in the form)
            raise ValidationError(file_data['error'])

        # Add file data if uploaded
        if file_data['file_content']:
            data_object['file'] = file_data['file_content']
            data_object['file_name'] = file_data['filename']

        # data_object['file'] = base64.b64encode(file_data) if file and helper.get_file_size(
        #     kwargs.get('file')) < 2000000 else False
        data_object['description'] = kwargs.get('description')
        data_object['leave_type'] = int(kwargs.get('leave_type'))
        data_object['start_date'] = start_date
        data_object['end_date'] = end_date
        request.env['de.leave'].browse(int(kwargs.get('id'))).write(data_object)
        request.session['success_message'] = 'Day off updated'
        return redirect(
            get_leave_page_url('list', parent_student_param=parent_student_param))

    @http.route(['/student/leaves/get'], auth="user", type="http", csrf=False)
    def get_leaves_data(self, **kwargs):
        domain = [('student_id', '=', int(kwargs.get('student_id')))] if kwargs.get('student_id') else []
        leaves = request.env["de.leave"].search(domain)
        data_leaves = []
        for leave in leaves:
            data = dict()
            data['id'] = leave.id
            data['start_date'] = leave.start_date
            data['end_date'] = leave.end_date
            data['student_id'] = leave.student_id.id
            data['leave_type'] = leave.leave_type
            data_leaves.append(data)
        return Response(json.dumps(data_leaves, default=str), content_type='application/json;charset=utf-8',
                        status=200)
