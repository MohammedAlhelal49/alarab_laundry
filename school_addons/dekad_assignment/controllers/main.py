from odoo import http, _
from odoo.http import route, request
from odoo.addons.portal.controllers import portal
import base64
from werkzeug.utils import redirect
from odoo.exceptions import AccessError, ValidationError


def get_assignment_page_url(key, parent_student_param=None, id=None):
    if key == "list":
        return f"/student/assignments/{parent_student_param}" if parent_student_param else "/student/assignments"
    elif key == "show":
        return f"/student/assignment/{id}?parent_student_param={parent_student_param}" if parent_student_param else f"/student/assignment/{id}"
    elif key == "home":
        return f"/my/home/{parent_student_param}" if parent_student_param else "/my/home"


def get_assignment_submission_page_url(key, parent_student_param=None, id=None):
    if key == "show":
        return f"/student/assignment/{id}/submission/?parent_student_param={parent_student_param}" if parent_student_param else f"/student/assignment/{id}/submission"
    elif key == "home":
        return f"/my/home/{parent_student_param}" if parent_student_param else "/my/home"
    elif key == "update":
        return f"/student/assignment/submission/update/{id}?parent_student_param={parent_student_param}" if parent_student_param else f"/student/assignment/submission/update/{id}"


class AssignmentWebsite(portal.CustomerPortal):
    @route(
        ["/student/assignments", "/student/assignments/<int:id>", "/student/assignments/<int:id>/page/<int:page>",
         "/student/assignments/page/<int:page>"],
        auth="user",
        website=True,
    )
    def assignments(self, date_begin=None, date_end=None, filterby=None, sortby='date_new', page=1, search='',
                    search_in='name', **kwargs):
        parent_student_param = kwargs.get("id")

        # SECURITY: Check if parent has access to this student
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # Redirect check
        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        student_assignment_env = request.env["de.assignment"]

        # FIXED: Proper domain construction for assignments (excluding drafts)
        if parent_student_param:
            domain = [('student_ids', 'in', [int(parent_student_param)]), ('state', '!=', 'draft')]
        else:
            current_student = request.env['de.student'].search([('user_id', '=', request.env.user.id)])
            if current_student:
                domain = [('student_ids', 'in', [current_student.id]), ('state', '!=', 'draft')]
            else:
                domain = [('id', '=', False)]

        searchbar_sorts = {
            'date_new': {'label': _('Newest'), 'order': 'create_date DESC'},
            'date_old': {'label': _('Oldest'), 'order': 'create_date'},
            'type': {'label': _('Type'), 'order': 'assignment_type'},
        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'Finished': {'label': _('Finished'), 'domain': [('state', '=', 'finish')]},
        }

        search_list = {
            'name': {'label': _('Name'), 'input': 'name', 'domain': [('name', 'ilike', search)]}
        }

        # Build search domain
        search_domain = []
        if not search_in:
            search_in = 'name'
        if search and search_in:
            search_domain = search_list[search_in]['domain']

        if not sortby:
            sortby = 'date_new'
        order = searchbar_sorts[sortby]['order']

        if not filterby:
            filterby = 'all'

        # Combine all domains
        final_domain = domain + searchbar_filters[filterby]['domain'] + search_domain

        # Use sudo() for parents to access student assignments
        if parent_student_param:
            student_assignment_count = student_assignment_env.sudo().search_count(final_domain)
        else:
            student_assignment_count = student_assignment_env.search_count(final_domain)

        # Prepare pager data
        page_url = get_assignment_page_url('list', parent_student_param)
        pager_data = portal.pager(
            url=page_url,
            total=student_assignment_count,
            page=page,
            step=self._items_per_page,
            url_args={'date_begin': date_begin,
                      'date_end': date_end, 'sortby': sortby, 'search': search, 'search_in': search_in,
                      'filterby': filterby, }
        )

        # Get recordset with proper permissions
        if parent_student_param:
            student_assignment = student_assignment_env.sudo().search(
                final_domain, order=order, limit=self._items_per_page, offset=pager_data["offset"]
            )
        else:
            student_assignment = student_assignment_env.search(
                final_domain, order=order, limit=self._items_per_page, offset=pager_data["offset"]
            )

        # Prepare template values
        values = self._prepare_portal_layout_values()

        assignment_submission_list = []
        for assignment in student_assignment:
            student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)

            data_object = {
                'id': assignment.id,
                'has_draft_submission': request.env['de.assignment.submission'].sudo().search_count(
                    [('student_id', '=', student_id),
                     ('assignment_id', '=', assignment.id),
                     ('state', '=', 'draft')])
            }
            assignment_submission_list.append(data_object)

        values.update({
            "assignment_records": student_assignment,
            "page_name": "Assignments",
            "default_url": page_url,
            "pager": pager_data,
            'date': date_begin,
            'date_end': date_end,
            'searchbar_sortings': searchbar_sorts,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'search': search,
            'search_in': search_in,
            'searchbar_inputs': search_list,
            "page_url": page_url,
            "home_url": get_assignment_page_url('home', parent_student_param),
            "parent_student_param": parent_student_param,
            'student': helper.get_student(parent_student_param),
            "assignment_submission_list": assignment_submission_list,
        })

        return request.render("dekad_assignment.student_assignment", values)

    @route("/student/assignment/<int:assignment_id>", auth='user', website=True)
    def assignment_show(self, assignment_id, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')

        # Load assignment with sudo for parents
        if parent_student_param:
            record = request.env['de.assignment'].sudo().browse(assignment_id)
        else:
            record = request.env['de.assignment'].browse(assignment_id)

        if not record.exists():
            raise ValidationError(_("Assignment not found."))

        # SECURITY: Check parent access
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # SECURITY: Check if assignment belongs to the student
        student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)
        if student_id not in record.student_ids.ids:
            raise AccessError(_("This assignment is not assigned to the specified student."))

        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        return http.request.render('dekad_assignment.student_assignment_show', {
            'page_name': 'Assignment Show',
            "home_url": get_assignment_page_url('home', parent_student_param),
            "list_url": get_assignment_page_url('list', parent_student_param),
            "page_url": get_assignment_page_url('show', parent_student_param, record.id),
            "record": record,
            "parent_student_param": parent_student_param,
            'student': helper.get_student(parent_student_param),
            'file_name': record.file_name or "",
        })

    @route(['/student/assignment/download/<int:assignment_id>'], type='http', auth="user")
    def assignment_download(self, assignment_id, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')

        # Load with sudo for parents
        record = request.env['de.assignment'].sudo().browse(assignment_id)

        if not record.exists():
            raise ValidationError(_("Assignment not found."))

        # SECURITY: Check parent access
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # SECURITY: Check if assignment belongs to the student
        student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)
        if student_id not in record.student_ids.ids:
            raise AccessError(_("This assignment is not assigned to the specified student."))

        # Use helper function for download
        # For new files: uses stored filename (with correct extension)
        # For old files: uses display_name without assuming file type
        return helper.download_file(
            record=record,
            field_name='file',
            filename_field='file_name',
            default_filename=record.display_name
        )

    # submission section
    @route(["/student/assignment/<int:assignment_id>/submission"], auth="user", website=True)
    def assignment_submission(self, assignment_id, **kwargs):
        success_message = request.session.get('success_message')
        request.session['success_message'] = ''
        parent_student_param = kwargs.get('parent_student_param')

        # Load assignment with sudo for parents
        if parent_student_param:
            assignment = request.env['de.assignment'].sudo().browse(assignment_id)
        else:
            assignment = request.env['de.assignment'].browse(assignment_id)

        if not assignment.exists():
            raise ValidationError(_("Assignment not found."))

        # SECURITY: Check parent access
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # SECURITY: Check if assignment belongs to the student
        student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)
        if student_id not in assignment.student_ids.ids:
            raise AccessError(_("This assignment is not assigned to the specified student."))

        # Get submission for specific student
        submission = request.env['de.assignment.submission'].sudo().search([
            ('assignment_id', '=', assignment.id),
            ('student_id', '=', student_id)
        ], limit=1)

        return http.request.render('dekad_assignment.student_assignment_submission', {
            'page_name': 'Assignment submission',
            "assignment_list_url": get_assignment_page_url('list', parent_student_param),
            "assignment_show_url": get_assignment_page_url('show', parent_student_param, assignment.id),
            "home_url": get_assignment_submission_page_url('home', parent_student_param),
            "page_url": get_assignment_submission_page_url('show', parent_student_param, assignment.id),
            "assignment": assignment,
            'submission': submission,
            'file_name': submission.file_name or "" if submission else "",
            "success_message": success_message or "",
            'student': helper.get_student(parent_student_param),
            "parent_student_param": parent_student_param,
        })

    @route(['/student/assignment/submission/download/<int:submission_id>',
            '/student/assignment/<int:assignment_id>/submission/download'],
           type='http', auth="user")
    def assignment_submission_download(self, submission_id=None, assignment_id=None, **kwargs):
        # Handle both URL patterns
        if assignment_id and not submission_id:
            # URL pattern: /student/assignment/{assignment_id}/submission/download
            # Need to find the submission for this assignment and current student
            parent_student_param = kwargs.get('parent_student_param')
            student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)

            submission = request.env['de.assignment.submission'].sudo().search([
                ('assignment_id', '=', assignment_id),
                ('student_id', '=', student_id)
            ], limit=1)

            if not submission:
                raise ValidationError(_("Submission not found."))

            record = submission
        else:
            # URL pattern: /student/assignment/submission/download/{submission_id}
            record = request.env['de.assignment.submission'].sudo().browse(submission_id)

        if not record.exists():
            raise ValidationError(_("Submission not found."))

        parent_student_param = kwargs.get('parent_student_param')

        # SECURITY: Check parent access
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # SECURITY: Check if submission belongs to the student
        student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)
        if record.student_id.id != student_id:
            raise AccessError(_("This submission does not belong to the specified student."))

        # Use helper function for download
        # For new files: uses stored filename (with correct extension)
        # For old files: uses display_name without assuming file type
        return helper.download_file(
            record=record,
            field_name='file',
            filename_field='file_name',
            default_filename=record.display_name
        )

    @route('/student/assignments/submission/create', auth='user', website=True, methods=['POST'])
    def assignment_submission_create_updated(self, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')

        # Process uploaded file using helper function
        file_data = helper.process_uploaded_file(kwargs.get('file'), max_size_mb=2)

        if file_data['error']:
            # Handle error (you might want to show this in the form)
            raise ValidationError(file_data['error'])

        # Get student ID
        student_id = request.env['de.student'].search([('user_id', '=', request.uid)]).id

        # Create submission
        data_object = {
            'student_id': student_id,
            'assignment_id': int(kwargs.get('assignment_id')),
            'description': kwargs.get('description', ''),
            'state': 'confirm',
        }

        # Add file data if uploaded
        if file_data['file_content']:
            data_object['file'] = file_data['file_content']
            data_object['file_name'] = file_data['filename']

        request.env["de.assignment.submission"].create(data_object)
        request.session['success_message'] = 'Assignment submission created'

        # Build redirect URL with parent_student_param if exists
        redirect_url = f"/student/assignment/{kwargs.get('assignment_id')}/submission"
        if parent_student_param:
            redirect_url += f"?parent_student_param={parent_student_param}"

        return redirect(redirect_url)

    @route(["/student/assignment/<int:assignment_id>/submission/update"], auth='user', website=True)
    def assignment_submission_update_form_updated(self, assignment_id, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')

        # Load assignment with sudo for parents
        if parent_student_param:
            assignment = request.env['de.assignment'].sudo().browse(assignment_id)
        else:
            assignment = request.env['de.assignment'].browse(assignment_id)

        if not assignment.exists():
            raise ValidationError(_("Assignment not found."))

        # SECURITY: Check parent access
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # Get the student's submission
        student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)
        submission = request.env['de.assignment.submission'].sudo().search([
            ('assignment_id', '=', assignment.id),
            ('student_id', '=', student_id)
        ], limit=1)

        if not submission:
            raise ValidationError(_("No submission found for this assignment."))

        return http.request.render('dekad_assignment.student_assignment_submission_update', {
            'page_name': 'Assignment submission update',
            "home_url": get_assignment_submission_page_url('home', parent_student_param),
            "page_url": get_assignment_submission_page_url('update', parent_student_param, submission.id),
            "assignment": assignment,
            "submission": submission,
            'list_url': get_assignment_page_url('list', parent_student_param),
            'assignment_url': get_assignment_page_url('show', parent_student_param, assignment.id),
            'file_name': submission.file_name or "",
            "parent_student_param": parent_student_param,
        })

    @route('/student/assignments/submission/update', type='http', website=True, auth='user', methods=['POST'])
    def assignment_submission_update_updated(self, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')
        submission_id = int(kwargs.get('id'))

        # Prepare data object
        data_object = {
            'description': kwargs.get('description', '')
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

        request.env['de.assignment.submission'].browse(submission_id).write(data_object)
        request.session['success_message'] = 'Assignment submission updated'

        # Build redirect URL with parent_student_param if exists
        redirect_url = f"/student/assignment/{kwargs['assignment_id']}/submission"
        if parent_student_param:
            redirect_url += f"?parent_student_param={parent_student_param}"

        return redirect(redirect_url)

    @route(["/student/assignment/<int:assignment_id>/submission/delete"], auth='user', website=True)
    def assignment_submission_delete(self, assignment_id, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')

        # Load assignment with sudo for parents
        if parent_student_param:
            assignment = request.env['de.assignment'].sudo().browse(assignment_id)
        else:
            assignment = request.env['de.assignment'].browse(assignment_id)

        if not assignment.exists():
            raise ValidationError(_("Assignment not found."))

        # SECURITY: Check parent access
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # Get the student's submission
        student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)
        submission = request.env['de.assignment.submission'].sudo().search([
            ('assignment_id', '=', assignment.id),
            ('student_id', '=', student_id)
        ], limit=1)

        if submission and submission.exists():
            submission.unlink()
            request.session['success_message'] = 'Assignment submission deleted'

        # Build redirect URL with parent_student_param if exists
        redirect_url = f"/student/assignment/{assignment.id}/submission"
        if parent_student_param:
            redirect_url += f"?parent_student_param={parent_student_param}"

        return redirect(redirect_url)