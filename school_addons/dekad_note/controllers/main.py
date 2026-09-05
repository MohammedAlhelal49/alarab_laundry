from odoo import http, _
from odoo.http import route, request
from odoo.addons.portal.controllers import portal
import base64
from werkzeug.utils import redirect
from odoo.exceptions import AccessError


def get_note_page_url(key, parent_student_param=None, id=None):
    if key == "list":
        return f"/student/notes/{parent_student_param}" if parent_student_param else f"/student/notes"
    elif key == "show":
        return f"/student/note/{id}?parent_student_param={parent_student_param}" if parent_student_param else f"/student/note/{id}"
    elif key == "home":
        return f"/my/home/{parent_student_param}" if parent_student_param else "/my/home"


class NoteWebsite(portal.CustomerPortal):

    @route(
        ["/student/notes", "/student/notes/<int:id>", "/student/notes/<int:id>/page/<int:page>",
         "/student/notes/page/<int:page>"],
        auth="user",
        website=True,
    )
    def notes(self, date_begin=None, date_end=None, filterby=None, sortby='priority', page=1, search='',
              search_in='name', **kwargs):

        parent_student_param = kwargs.get("id")
        user = request.env.user

        # SECURITY: Check if parent has access to this specific student
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # Determine if this is a parent's general page (no specific student)
        parent_page = user.is_parent and not parent_student_param

        if parent_page:
            # Parent viewing their own notes (general parent notes)
            parent_record = request.env['de.parent'].search([('user_id', '=', user.id)])
            if not parent_record:
                return redirect('/my/home')

            domain = ['|',
                      ('group_id.all_parents', '=', True),
                      ('group_id.parent_ids', 'in', [parent_record.id])
                      ]
            use_sudo = False  # Parents can access their own notes directly

        elif parent_student_param:
            # Parent viewing specific student's notes - ONLY student notes with confirmed status
            domain = [
                '&',  # AND condition for status
                '|',  # OR condition for student access
                # Student-specific notes
                ('group_id.student_ids', 'in', [int(parent_student_param)]),
                # All students notes
                ('group_id.all_students', '=', True),
                # ONLY confirmed notes
                ('state', '=', 'confirm')
            ]
            use_sudo = True  # Parents need sudo to access student notes

        else:
            # Student viewing their own notes
            domain = ['|',
                      ('group_id.student_ids.user_id', '=', user.id),
                      ('group_id.all_students', '=', True)
                      ]
            use_sudo = False  # Students can access their own notes directly

        # Redirect check
        if not parent_page and helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        print(f"User: {user.name}, is_parent: {getattr(user, 'is_parent', False)}")
        print(f"Parent student param: {parent_student_param}")
        print(f"Parent page: {parent_page}")
        print(f"Domain: {domain}")
        print(f"Use sudo: {use_sudo}")

        student_note_env = request.env["de.note"]
        if use_sudo:
            student_note_env = student_note_env.sudo()

        searchbar_sorts = {
            'priority': {'label': _('Priority'), 'order': 'priority DESC'},
            'date_new': {'label': _('Newest'), 'order': 'create_date DESC'},
            'date_old': {'label': _('Oldest'), 'order': 'create_date'},
        }

        if not sortby:
            sortby = 'priority'
        order = searchbar_sorts[sortby]['order']

        search_list = {
            'name': {'label': _('Name'), 'input': 'name', 'domain': [('name', 'ilike', search)]}
        }

        # Add search domain if provided
        search_domain = []
        if not search_in:
            search_in = 'name'
        if search and search_in:
            search_domain = search_list[search_in]['domain']

        # Combine base domain with search domain
        final_domain = domain + search_domain
        print(f"Final domain: {final_domain}")

        # Get count and records with proper permissions
        student_note_count = student_note_env.search_count(final_domain)
        print(f"Notes count: {student_note_count}")

        # Prepare pager data
        page_url = get_note_page_url('list', parent_student_param)
        pager_data = portal.pager(
            url=page_url,
            total=student_note_count,
            page=page,
            step=self._items_per_page,
            url_args={
                'date_begin': date_begin,
                'date_end': date_end,
                'sortby': sortby,
                'filterby': filterby,
                'search': search,
                'search_in': search_in
            }
        )

        # Get note records with proper permissions
        student_note = student_note_env.search(
            final_domain,
            order=order,
            limit=self._items_per_page,
            offset=pager_data["offset"]
        )

        print(f"Found note records: {len(student_note)}")

        # Prepare template values
        values = self._prepare_portal_layout_values()
        values.update({
            "page_name": "Notes",
            "page_url": page_url,
            "home_url": get_note_page_url('home', parent_student_param),
            "note_records": student_note,
            "default_url": page_url,
            "pager": pager_data,
            'date': date_begin,
            'date_end': date_end,
            'searchbar_sortings': searchbar_sorts,
            'sortby': sortby,
            'filterby': filterby,
            'search': search,
            'search_in': search_in,
            'searchbar_inputs': search_list,
            "parent_student_param": parent_student_param,
            'student': helper.get_student(parent_student_param)
        })

        return request.render("dekad_note.student_note", values)

    @route("/student/note/<int:note_id>", auth='user', website=True)
    def note_show(self, note_id, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')
        user = request.env.user

        # SECURITY: Check if parent has access to this specific student
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        parent_page = user.is_parent and not parent_student_param

        # Read the record with sudo (we'll verify access below)
        record = request.env['de.note'].sudo().browse(note_id)
        if not record.exists():
            raise AccessError(_("Note not found."))

        # SECURITY: Verify user can access this specific note
        if parent_student_param:
            # Parent viewing student's note - check if note is accessible to this student AND confirmed
            student_has_access = (
                    (record.group_id.all_students or
                     int(parent_student_param) in record.group_id.student_ids.ids) and
                    record.state == 'confirm'  # ONLY confirmed notes
            )
            if not student_has_access:
                raise AccessError(_("This note is not accessible for the specified student or not confirmed."))

        elif parent_page:
            # Parent viewing their own note
            parent_record = request.env['de.parent'].search([('user_id', '=', user.id)])
            parent_has_access = (
                    record.group_id.all_parents or
                    (parent_record and parent_record.id in record.group_id.parent_ids.ids)
            )
            if not parent_has_access:
                raise AccessError(_("You don't have access to this note."))

        else:
            # Student viewing note
            current_student = request.env['de.student'].search([('user_id', '=', user.id)])
            student_has_access = (
                    record.group_id.all_students or
                    (current_student and current_student.id in record.group_id.student_ids.ids)
            )
            if not student_has_access:
                raise AccessError(_("You don't have access to this note."))

        # Redirect checks
        if parent_page:
            if not user.is_parent:
                return redirect('/my/home')
        else:
            if helper.redirect_portal_page(parent_student_param):
                return redirect(helper.redirect_portal_page(parent_student_param))

        model_attachment = {
            "model": "de.note",
            "field": "file",
            "id": record.id,
        }
        data_object = helper.get_file_attachment_type(model_attachment)
        file_name = record.file_name
        file_type = data_object['file_type']

        return http.request.render('dekad_note.student_note_show', {
            'page_name': 'Note Show',
            "home_url": get_note_page_url('home', parent_student_param),
            "list_url": get_note_page_url('list', parent_student_param),
            "page_url": get_note_page_url('show', parent_student_param, record.id),
            "record": record,
            'parent_student_param': parent_student_param,
            'student': helper.get_student(parent_student_param),
            'file_name': f"{file_name}" if data_object['attachment'] else "",
        })

    @route('/student/note/download/<int:note_id>', type='http', auth="user")
    def note_download(self, note_id, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')
        user = request.env.user

        # SECURITY: Check if parent has access to this specific student
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # Read the record with sudo (we'll verify access below)
        record = request.env['de.note'].sudo().browse(note_id)
        if not record.exists():
            raise AccessError(_("Note not found."))

        # SECURITY: Verify user can access this specific note (same logic as note_show)
        if parent_student_param:
            student_has_access = (
                    (record.group_id.all_students or
                     int(parent_student_param) in record.group_id.student_ids.ids) and
                    record.state == 'confirm'  # ONLY confirmed notes
            )
            if not student_has_access:
                raise AccessError(_("This note is not accessible for the specified student or not confirmed."))

        elif user.is_parent:
            parent_record = request.env['de.parent'].search([('user_id', '=', user.id)])
            parent_has_access = (
                    record.group_id.all_parents or
                    (parent_record and parent_record.id in record.group_id.parent_ids.ids)
            )
            if not parent_has_access:
                raise AccessError(_("You don't have access to this note."))

        else:
            current_student = request.env['de.student'].search([('user_id', '=', user.id)])
            student_has_access = (
                    record.group_id.all_students or
                    (current_student and current_student.id in record.group_id.student_ids.ids)
            )
            if not student_has_access:
                raise AccessError(_("You don't have access to this note."))

        # Get the attachment using sudo for file access
        attachment = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'de.note'),
            ('res_field', '=', 'file'),
            ('res_id', '=', record.id)
        ], limit=1)

        if not attachment:
            raise AccessError(_("File not found for this note."))

        # Get file content from attachment (with sudo)
        file_content = base64.b64decode(attachment.datas)

        # Determine file extension
        # file_type = attachment.mimetype.split('/')[-1] if attachment.mimetype else 'pdf'
        # if file_type == 'vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        #     file_type = 'xlsx'
        # elif file_type == 'vnd.openxmlformats-officedocument.wordprocessingml.document':
        #     file_type = 'docx'
        # elif file_type == 'plain':
        #     file_type = 'txt'

        headers = [
            ('Content-Type', attachment.mimetype or 'application/octet-stream'),
            ('Content-Disposition', f'attachment; filename="note - {record.flie_name}"'),
            ('Content-Length', len(file_content))
        ]

        return request.make_response(file_content, headers=headers)