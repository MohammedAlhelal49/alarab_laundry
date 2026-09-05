from odoo import http, _
from odoo.http import route, request
from odoo.addons.portal.controllers import portal
import base64
from werkzeug.utils import redirect
from odoo.exceptions import AccessError, ValidationError



def get_complaint_page_url(key, parent_student_param=None, id=None):
    if key == "list":
        return f"/student/complaints/{parent_student_param}" if parent_student_param else f"/student/complaints"
    elif key == "show":
        return f"/student/complaint/{id}?parent_student_param={parent_student_param}" if parent_student_param else f"/student/complaint/{id}"
    elif key == "home":
        return f"/my/home/{parent_student_param}" if parent_student_param else "/my/home"
    elif key == "create":
        return f"/student/complaint/create?parent_student_param={parent_student_param}" if parent_student_param else "/student/complaint/create"
    elif key == "update":
        return f"/student/complaint/update/{id}?parent_student_param={parent_student_param}" if parent_student_param else f"/student/complaint/update/{id}"


class ComplaintWebsite(portal.CustomerPortal):

    @route(
        ["/student/complaints", "/student/complaints/<int:id>", "/student/complaints/<int:id>/page/<int:page>",
         "/student/complaints/page/<int:page>"],
        auth="user",
        website=True,
    )
    def complaints(self, date_begin=None, date_end=None, filterby=None, sortby='date_new', page=1, **kwargs):
        success_message = request.session.get('success_message')
        request.session['success_message'] = ''

        parent_student_param = kwargs.get("id")
        parent_page = request.env.user.is_parent and not parent_student_param

        # Domain based on user type
        if parent_page:
            # Parent viewing their own complaints
            domain = [('parent_id.user_id', '=', request.env.user.id)]
            if not request.env.user.is_parent:
                return redirect('/my/home')
        else:
            # Student or parent viewing specific student
            domain = [('student_id', '=', parent_student_param)] if parent_student_param else []

            # SECURITY: Check parent access
            if parent_student_param and not helper.check_parent_student(parent_student_param):
                raise AccessError(_("You don't have permission to access this student's information."))

            if helper.redirect_portal_page(parent_student_param):
                return redirect(helper.redirect_portal_page(parent_student_param))

        student_complaint_env = request.env["de.complaint"]

        searchbar_sorts = {
            'date_new': {'label': _('Newest'), 'order': 'create_date DESC'},
            'date_old': {'label': _('Oldest'), 'order': 'create_date'},
            'state': {'label': _('State'), 'order': 'state'},
        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'action': {'label': _('Action taken'), 'domain': [('state', '=', 'action')]},
            'reject': {'label': _('Rejected'), 'domain': [('state', '=', 'reject')]},
        }

        if not sortby:
            sortby = 'date_new'
        order = searchbar_sorts[sortby]['order']

        if not filterby:
            filterby = 'all'

        domain += searchbar_filters[filterby]['domain']

        # Use sudo for parents viewing student complaints
        if parent_student_param:
            student_complaint_count = student_complaint_env.sudo().search_count(domain)
        else:
            student_complaint_count = student_complaint_env.search_count(domain)

        # Prepare pager data
        page_url = get_complaint_page_url('list', parent_student_param)
        pager_data = portal.pager(
            url=page_url,
            total=student_complaint_count,
            page=page,
            step=self._items_per_page,
            url_args={'date_begin': date_begin,
                      'date_end': date_end, 'sortby': sortby,
                      'filterby': filterby, }
        )

        # Get recordset with proper permissions
        if parent_student_param:
            student_complaint = student_complaint_env.sudo().search(
                domain, order=order, limit=self._items_per_page, offset=pager_data["offset"]
            )
        else:
            student_complaint = student_complaint_env.search(
                domain, order=order, limit=self._items_per_page, offset=pager_data["offset"]
            )

        # Prepare template values
        values = self._prepare_portal_layout_values()
        values.update({
            "page_name": "Complaints",
            "create_url": get_complaint_page_url('create', parent_student_param),
            "page_url": page_url,
            "home_url": get_complaint_page_url('home', parent_student_param),
            "complaint_records": student_complaint,
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
        })

        return request.render("dekad_complaint.student_complaint", values)

    @route('/student/complaint/delete/<int:complaint_id>', auth='user', website=True)
    def complaint_delete(self, complaint_id, **kwargs):
        parent_student_param = int(kwargs.get('parent_student_param')) if kwargs.get('parent_student_param') else None

        # Load with sudo for parents
        if parent_student_param:
            record = request.env['de.complaint'].sudo().browse(complaint_id)
        else:
            record = request.env['de.complaint'].browse(complaint_id)

        if not record.exists():
            raise ValidationError(_("Complaint not found."))

        # SECURITY: Check parent access
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # Verify ownership
        student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)
        if record.student_id.id != student_id:
            raise AccessError(_("This complaint does not belong to the specified student."))

        record.unlink()
        request.session['success_message'] = 'Complaint deleted'

        return redirect(get_complaint_page_url('list', parent_student_param=parent_student_param))

    @route("/student/complaint/<int:complaint_id>", auth='user', website=True)
    def complaint_show(self, complaint_id, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')
        parent_page = request.env.user.is_parent and not parent_student_param

        # Load with sudo for parents
        if parent_student_param:
            record = request.env['de.complaint'].sudo().browse(complaint_id)
        else:
            record = request.env['de.complaint'].browse(complaint_id)

        if not record.exists():
            raise ValidationError(_("Complaint not found."))

        if parent_page:
            if not request.env.user.is_parent:
                return redirect('/my/home')
        else:
            # SECURITY: Check parent access
            if parent_student_param and not helper.check_parent_student(parent_student_param):
                raise AccessError(_("You don't have permission to access this student's information."))

            if helper.redirect_portal_page(parent_student_param):
                return redirect(helper.redirect_portal_page(parent_student_param))

        return http.request.render('dekad_complaint.student_complaint_show', {
            'page_name': 'Complaint Show',
            "home_url": get_complaint_page_url('home', parent_student_param),
            "list_url": get_complaint_page_url('list', parent_student_param),
            "page_url": get_complaint_page_url('show', parent_student_param, record.id),
            "record": record,
            "parent_student_param": parent_student_param,
            'student': helper.get_student(parent_student_param),
            'file_name': record.file_name or "",
        })

    @route(['/student/complaint/download/<int:complaint_id>'], type='http', auth="user")
    def complaint_download(self, complaint_id, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')

        # Load with sudo for parents
        if parent_student_param:
            record = request.env['de.complaint'].sudo().browse(complaint_id)
        else:
            record = request.env['de.complaint'].browse(complaint_id)

        if not record.exists():
            raise ValidationError(_("Complaint not found."))

        # SECURITY: Check parent access
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # Verify ownership
        student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)
        if record.student_id and record.student_id.id != student_id:
            raise AccessError(_("This complaint does not belong to the specified student."))

        # Use helper function for download
        # For new files: uses stored filename (with correct extension)
        # For old files: uses generic name without assuming file type
        default_name = f"{record.student_id.name} - complaint" if record.student_id else "complaint"

        return helper.download_file(
            record=record,
            field_name='file',
            filename_field='file_name',
            default_filename=default_name
        )

    @route("/student/complaint/create", auth='user', website=True, methods=['GET'])
    def complaint_create_form(self, **kwargs):
        parent_student_param = int(kwargs.get('parent_student_param')) if kwargs.get('parent_student_param') else None
        parent_page = request.env.user.is_parent and not parent_student_param

        if parent_page:
            if not request.env.user.is_parent:
                return redirect('/my/home')
        else:
            # SECURITY: Check parent access
            if parent_student_param and not helper.check_parent_student(parent_student_param):
                raise AccessError(_("You don't have permission to access this student's information."))

            if helper.redirect_portal_page(parent_student_param):
                return redirect(helper.redirect_portal_page(parent_student_param))

        categories = request.env['de.complaint.category'].search([])
        grades = request.env['de.grade'].search([])

        return http.request.render('dekad_complaint.student_complaint_create', {
            'page_name': 'Complaint Create',
            "home_url": get_complaint_page_url('home', parent_student_param),
            "page_url": get_complaint_page_url('create', parent_student_param),
            "categories": categories,
            "grades": grades,
            'student_id': helper.get_student_id(parent_student_param),
            "parent_student_param": parent_student_param,
            'student': helper.get_student(parent_student_param),
            'list_url': get_complaint_page_url('list', parent_student_param)
        })

    @route('/student/complaint/create', auth='user', website=True, methods=['POST'])
    def complaint_create(self, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')
        parent_page = request.env.user.is_parent and not parent_student_param

        # SECURITY: Check parent access
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # Process uploaded file using helper function
        file_data = helper.process_uploaded_file(kwargs.get('file'), max_size_mb=2)

        if file_data['error']:
            raise ValidationError(file_data['error'])

        # Prepare complaint data
        data_object = {
            'student_id': int(kwargs.get('student_id')) if not parent_page else False,
            'description': kwargs.get('description'),
            'category_id': int(kwargs.get('category_id')),
            'parent_id': int(request.env['de.parent'].search(
                [('user_id', '=', request.env.user.id)]).id) if request.env.user.is_parent else False,
            'state': 'confirm',
            'subject': kwargs.get('subject')
        }

        # Add file data if uploaded
        if file_data['file_content']:
            data_object['file'] = file_data['file_content']
            data_object['file_name'] = file_data['filename']

        request.env["de.complaint"].create(data_object)
        request.session['success_message'] = 'Complaint created'

        return redirect(get_complaint_page_url('list', parent_student_param=parent_student_param))

    @route("/student/complaint/update/<int:complaint_id>", auth='user', website=True)
    def complaint_update_form(self, complaint_id, **kwargs):
        parent_student_param = int(kwargs.get('parent_student_param')) if kwargs.get('parent_student_param') else None
        parent_page = request.env.user.is_parent and not parent_student_param

        # Load with sudo for parents
        if parent_student_param:
            record = request.env['de.complaint'].sudo().browse(complaint_id)
        else:
            record = request.env['de.complaint'].browse(complaint_id)

        if not record.exists():
            raise ValidationError(_("Complaint not found."))

        if parent_page:
            if not request.env.user.is_parent:
                return redirect('/my/home')
        else:
            # SECURITY: Check parent access
            if parent_student_param and not helper.check_parent_student(parent_student_param):
                raise AccessError(_("You don't have permission to access this student's information."))

            if helper.redirect_portal_page(parent_student_param):
                return redirect(helper.redirect_portal_page(parent_student_param))

        categories = request.env['de.complaint.category'].search([])
        grades = request.env['de.grade'].search([])

        return http.request.render('dekad_complaint.student_complaint_update', {
            'page_name': 'Complaint Update',
            "home_url": get_complaint_page_url('home', parent_student_param),
            "page_url": get_complaint_page_url('update', parent_student_param, record.id),
            "show_url": get_complaint_page_url('show', parent_student_param, record.id),
            "grades": grades,
            "categories": categories,
            "record": record,
            'student_id': helper.get_student_id(parent_student_param),
            "parent_student_param": parent_student_param,
            'student': helper.get_student(parent_student_param),
            'list_url': get_complaint_page_url('list', parent_student_param),
            'file_name': record.file_name or "",
        })

    @route('/student/complaint/update', type='http', website=True, auth='user', methods=['POST'])
    def complaint_update(self, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')
        parent_page = request.env.user.is_parent and not parent_student_param
        complaint_id = int(kwargs.get('id'))

        # SECURITY: Check parent access
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # Prepare data object
        data_object = {
            'student_id': int(kwargs.get('student_id')) if not parent_page else False,
            'description': kwargs.get('description'),
            'category_id': int(kwargs.get('category_id')),
            'parent_id': int(request.env['de.parent'].search(
                [('user_id', '=', request.env.user.id)]).id) if request.env.user.is_parent else False,
            'subject': kwargs.get('subject')
        }

        # Process uploaded file if provided using helper function
        uploaded_file = kwargs.get('file')
        if uploaded_file and uploaded_file.filename:
            file_data = helper.process_uploaded_file(uploaded_file, max_size_mb=2)

            if file_data['error']:
                raise ValidationError(file_data['error'])

            if file_data['file_content']:
                data_object['file'] = file_data['file_content']
                data_object['file_name'] = file_data['filename']

        request.env['de.complaint'].browse(complaint_id).write(data_object)
        request.session['success_message'] = 'Complaint updated'

        return redirect(get_complaint_page_url('list', parent_student_param=parent_student_param))