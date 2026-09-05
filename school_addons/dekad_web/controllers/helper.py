from odoo.http import request
from werkzeug.utils import redirect
from odoo.exceptions import ValidationError
from odoo import _
import base64
import mimetypes
import os


def check_parent_student(parent_student_param):
    """
    SECURITY CRITICAL: Check if current parent user has access to this specific student
    Returns True only if parent is authorized to view this student
    """
    if not parent_student_param:
        return True

    user = request.env.user
    if not user.is_parent:
        return True  # Let other logic handle non-parents

    try:
        parent_student_id = int(parent_student_param)
    except (ValueError, TypeError):
        return False

    # Get the parent record for this user
    parent_record = request.env['de.parent'].sudo().search([('user_id', '=', user.id)])
    if not parent_record:
        return False  # Parent record doesn't exist

    # Check if this student is linked to this parent
    student_ids = parent_record.student_ids.ids
    return parent_student_id in student_ids


def redirect_portal_page(parent_student_param, is_customer_portal=False):
    """
    Enhanced redirect logic with proper security checks
    """
    parent_student_param = int(parent_student_param) if parent_student_param else parent_student_param
    user = request.env.user
    redirect_case = False

    if is_customer_portal:
        if user.has_group('base.group_portal') and not (user.is_student or user.is_parent):
            redirect_case = '/my/home'
        elif (user.has_group('base.group_user') or user.is_student) and parent_student_param:
            redirect_case = '/my/home'
        elif user.is_parent and parent_student_param:
            # CRITICAL: Check if parent is authorized for this specific student
            if not check_parent_student(parent_student_param):
                redirect_case = '/my/students'  # Redirect unauthorized access to student list
            else:
                redirect_case = False  # Allow access
        elif user.is_parent and not parent_student_param:
            redirect_case = False  # Allow parent to access general portal
    else:
        if user.has_group('base.group_portal') and not (user.is_student or user.is_parent):
            redirect_case = '/my/home'
        elif (user.has_group('base.group_user')) or (user.is_student and parent_student_param):
            redirect_case = '/my/home'
        elif user.is_parent:
            if not parent_student_param:
                redirect_case = False  # Allow parent general access
            else:
                redirect_case = '/my/students' if not check_parent_student(parent_student_param) else False

    # Check for blocked/suspended students
    redirect_case = '/blocked' if user and user.is_student and (user.is_suspended or user.is_blocked) else redirect_case

    return redirect_case


def access_customer_document(model, parent_student_param):
    """
    Enhanced document access with proper parent/student differentiation
    """
    user = request.env.user
    data_object = {'show': False, 'url': '', 'count': None}

    # Define domain for database queries
    if parent_student_param:
        domain = [('student_id', '=', int(parent_student_param))]
    else:
        current_student = request.env['de.student'].sudo().search([('user_id', '=', request.env.user.id)])
        domain = [('student_id', '=', current_student.id)] if current_student else []

    # Parent's own profile access
    if user.is_parent and model == 'parent_profile' and not parent_student_param:
        data_object['show'] = True
        data_object['url'] = '/parent/profile'
        data_object['count'] = None

    if user.is_student:
        # Students get full access (create, read, update, delete)
        data_object['show'] = True
        if model == 'profile':
            data_object['url'] = '/student/profile'
        elif model == 'fee':
            data_object['url'] = '/student/fees'
        elif model == 'health':
            data_object['url'] = '/student/health'
        elif model == 'complaint':
            data_object['url'] = '/student/complaints'
        elif model == 'note':
            data_object['url'] = '/student/notes'
        elif model == 'contravention':
            data_object['url'] = '/student/contraventions'
        elif model == 'attendance':
            data_object['url'] = '/student/attendance'
        elif model == 'achievement':
            data_object['url'] = '/student/achievements'
        elif model == 'activity':
            data_object['url'] = '/student/activities'
        elif model == 'leave':
            data_object['url'] = '/student/leaves'
        elif model == 'assignment':
            data_object['url'] = '/student/assignments'
        elif model == 'quiz':
            data_object['url'] = '/student/quizzes'
            # Students get access to their timetable
        elif model == 'timetable':
            data_object['url'] = '/student/timetable'
            data_object['show'] = True

    elif user.is_parent and parent_student_param:
        # Parents get read-only access with student ID in URL
        data_object['show'] = True
        if model == 'profile':
            data_object['url'] = f'/student/profile/{parent_student_param}'
        elif model == 'fee':
            data_object['url'] = f'/student/fees/{parent_student_param}'
        elif model == 'health':
            data_object['url'] = f'/student/health/{parent_student_param}'
        elif model == 'complaint':
            data_object['url'] = f'/student/complaints/{parent_student_param}'
        elif model == 'note':
            data_object['url'] = f'/student/notes/{parent_student_param}'
        elif model == 'contravention':
            data_object['url'] = f'/student/contraventions/{parent_student_param}'
        elif model == 'attendance':
            data_object['url'] = f'/student/attendance/{parent_student_param}'
        elif model == 'achievement':
            data_object['url'] = f'/student/achievements/{parent_student_param}'
        elif model == 'activity':
            data_object['url'] = f'/student/activities/{parent_student_param}'
        elif model == 'leave':
            data_object['url'] = f'/student/leaves/{parent_student_param}'
        elif model == 'assignment':
            data_object['url'] = f'/student/assignments/{parent_student_param}'
        elif model == 'quiz':
            data_object['url'] = f'/student/quizzes/{parent_student_param}'
        # Parents get access to their child's timetable
        elif model == 'timetable':
            data_object['url'] = f'/student/timetable/{parent_student_param}'
            data_object['show'] = True

    # Get counts for all document types (use sudo for database access)
    try:
        if model == "fee":
            data_object['count'] = request.env["de.student.fee"].sudo().search_count(domain)
        elif model == "health":
            data_object['count'] = request.env["de.health.checkup"].sudo().search_count(domain)
        elif model == "complaint":
            data_object['count'] = request.env["de.complaint"].sudo().search_count(domain)
        elif model == "contravention":
            data_object['count'] = request.env["de.contravention"].sudo().search_count(domain)
        elif model == "attendance":
            data_object['count'] = request.env["de.attendance.line"].sudo().search_count(domain)
        elif model == "achievement":
            data_object['count'] = request.env["de.student.achievement.assign"].sudo().search_count(domain)
        elif model == "activity":
            data_object['count'] = request.env["de.activity"].sudo().search_count(domain)
        elif model == "leave":
            data_object['count'] = request.env["de.leave"].sudo().search_count(domain)
        elif model == "assignment":
            # Proper assignment count for parents (excluding drafts)
            if parent_student_param:
                assignment_domain = [('student_ids', 'in', [int(parent_student_param)]), ('state', '!=', 'draft')]
            else:
                current_student = request.env['de.student'].sudo().search([('user_id', '=', request.env.user.id)])
                if current_student:
                    assignment_domain = [('student_ids', 'in', [current_student.id]), ('state', '!=', 'draft')]
                else:
                    assignment_domain = [('id', '=', False)]
            data_object['count'] = request.env["de.assignment"].sudo().search_count(assignment_domain)
        elif model == "quiz":
            # Similar fix for quizzes
            if parent_student_param:
                quiz_domain = [('student_ids', 'in', [int(parent_student_param)])]
            else:
                current_student = request.env['de.student'].sudo().search([('user_id', '=', request.env.user.id)])
                if current_student:
                    quiz_domain = [('student_ids', 'in', [current_student.id])]
                else:
                    quiz_domain = [('id', '=', False)]
            data_object['count'] = request.env["de.quiz"].sudo().search_count(quiz_domain)
        elif model == "note":
            if parent_student_param:
                note_domain = ['|', ('group_id.student_ids.id', '=', int(parent_student_param)),
                               ('group_id.all_students', '=', True)]
            else:
                note_domain = ['|', ('group_id.student_ids.user_id', '=', request.env.user.id),
                               ('group_id.all_students', '=', True)]
            data_object['count'] = request.env["de.note"].sudo().search_count(note_domain)
        elif model == "timetable":
            if parent_student_param:
                student = request.env['de.student'].sudo().browse(int(parent_student_param))
            else:
                student = request.env['de.student'].sudo().search([('user_id', '=', request.env.user.id)])

            if student and student.grade and student.classroom_id:
                timetable_count = request.env["de.timetable"].sudo().search_count([
                    ('grade_id', '=', student.grade.id),
                    ('classroom_id', '=', student.classroom_id.id)
                ])
                data_object['count'] = timetable_count
            else:
                data_object['count'] = 0
    except Exception as e:
        # Handle any database access errors gracefully
        print(f"Error getting count for {model}: {e}")
        data_object['count'] = 0

    return data_object


# ============================================================================
# FILE HANDLING UTILITIES - REUSABLE ACROSS ALL MODELS
# ============================================================================

def get_mime_type(filename):
    """
    Determine MIME type from filename with comprehensive fallback
    Supports all common file types

    Args:
        filename (str): The filename with extension

    Returns:
        str: MIME type string (e.g., 'application/pdf')
    """
    if not filename:
        return 'application/octet-stream'

    # Initialize mimetypes if not already done
    if not mimetypes.inited:
        mimetypes.init()

    # Get file extension
    _, ext = os.path.splitext(filename.lower())

    # Try to guess MIME type
    mime_type, _ = mimetypes.guess_type(filename)

    # If mimetypes can't determine, use manual mapping for common types
    if not mime_type:
        mime_map = {
            # Documents
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.odt': 'application/vnd.oasis.opendocument.text',
            '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
            '.odp': 'application/vnd.oasis.opendocument.presentation',

            # Text
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.xml': 'text/xml',
            '.json': 'application/json',

            # Images
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.webp': 'image/webp',

            # Archives
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed',
            '.7z': 'application/x-7z-compressed',
            '.tar': 'application/x-tar',
            '.gz': 'application/gzip',

            # Audio
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4',

            # Video
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.wmv': 'video/x-ms-wmv',
            '.flv': 'video/x-flv',
            '.webm': 'video/webm',
            '.mkv': 'video/x-matroska',
        }
        mime_type = mime_map.get(ext, 'application/octet-stream')

    return mime_type


def download_file(record, field_name='file', filename_field='file_name', default_filename=None):
    """
    Universal file download function for any Odoo model

    Args:
        record: Odoo recordset (single record)
        field_name: Name of the Binary field containing file data (default: 'file')
        filename_field: Name of the Char field containing filename (default: 'file_name')
        default_filename: Fallback filename if filename_field is empty

    Returns:
        HTTP response with file download

    Example usage in controller:
        return helper.download_file(assignment_record, 'file', 'file_name', 'assignment.pdf')
    """
    # Get file content
    file_data = getattr(record, field_name, None)
    if not file_data:
        raise ValidationError(_("No file attached to this record."))

    # Decode binary data
    file_content = base64.b64decode(file_data)

    # Get filename
    filename = getattr(record, filename_field, None)
    if not filename:
        filename = default_filename or f"{record.display_name}.pdf"

    # Get MIME type
    mime_type = get_mime_type(filename)

    # Prepare headers
    headers = [
        ('Content-Type', mime_type),
        ('Content-Disposition', f'attachment; filename="{filename}"'),
        ('Content-Length', len(file_content))
    ]

    return request.make_response(file_content, headers=headers)


def process_uploaded_file(uploaded_file, max_size_mb=2):
    """
    Process an uploaded file from a form

    Args:
        uploaded_file: werkzeug FileStorage object from request
        max_size_mb: Maximum file size in megabytes (default: 2MB)

    Returns:
        dict: {
            'file_content': base64 encoded file content or False,
            'filename': original filename or False,
            'error': error message if any
        }

    Example usage in controller:
        file_data = helper.process_uploaded_file(request.files.get('file'))
        if file_data['error']:
            # Handle error
        else:
            vals = {
                'file': file_data['file_content'],
                'file_name': file_data['filename']
            }
    """
    result = {
        'file_content': False,
        'filename': False,
        'error': None
    }

    if not uploaded_file or not uploaded_file.filename:
        return result

    try:
        # Read file content
        file_content = uploaded_file.read()

        # Check file size
        max_size_bytes = max_size_mb * 1024 * 1024
        if len(file_content) >= max_size_bytes:
            result['error'] = _(f"File size must be less than {max_size_mb}MB.")
            return result

        # Encode to base64
        result['file_content'] = base64.b64encode(file_content)
        result['filename'] = uploaded_file.filename

    except Exception as e:
        result['error'] = _("Error processing file: %s") % str(e)

    return result


def get_file_extension_from_filename(filename):
    """
    Extract file extension from filename

    Args:
        filename (str): The filename

    Returns:
        str: File extension without dot (e.g., 'pdf', 'docx')
    """
    if not filename:
        return ''

    _, ext = os.path.splitext(filename.lower())
    return ext.lstrip('.')


# ============================================================================
# DEPRECATED - Keep for backward compatibility, will be removed in future
# ============================================================================

def get_file_attachment_type(model):
    """
    DEPRECATED: This function is kept for backward compatibility only.
    Use record.file_name instead for new code.

    For new implementations, store filename in a Char field alongside Binary field.
    """
    data_object = {'attachment': None, 'file_type': None}

    try:
        attachment = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', model['model']),
            ('res_field', '=', model['field']),
            ('res_id', '=', model['id'])
        ])

        if attachment and attachment.name:
            # Try to extract extension from attachment name
            file_type = get_file_extension_from_filename(attachment.name)
            data_object['file_type'] = file_type

        data_object['attachment'] = attachment
    except Exception as e:
        print(f"Error in get_file_attachment_type: {e}")

    return data_object


# ============================================================================
# OTHER UTILITY FUNCTIONS
# ============================================================================

def get_student_id(parent_student_param):
    """Safe student ID retrieval"""
    try:
        student_env = request.env['de.student'].sudo()
        if parent_student_param:
            return int(parent_student_param)
        else:
            student = student_env.search([('user_id', '=', request.env.user.id)])
            return student.id if student else None
    except Exception:
        return None


def get_student(parent_student_param=False):
    """Safe student record retrieval"""
    try:
        student_env = request.env['de.student'].sudo()
        if parent_student_param:
            return student_env.browse(int(parent_student_param))
        else:
            return student_env.sudo().search([('user_id', '=', request.env.user.id)])
    except Exception:
        return student_env.browse([])  # Return empty recordset


def get_selection_label(model):
    """Safe selection field label retrieval"""
    try:
        field_id = request.env['ir.model.fields'].sudo().search([
            ('model', '=', model['model']),
            ('name', '=', model['field'])
        ])

        if field_id:
            selection_record = request.env['ir.model.fields.selection'].sudo().search([
                ('field_id', '=', field_id[0].id)
            ])
            matching_selection = selection_record.filtered(
                lambda obj: obj.value == model['record'][model['field']]
            )
            return matching_selection[0].name if matching_selection else 'Unknown'
        return 'Unknown'
    except Exception:
        return 'Unknown'


def get_file_size(file):
    """
    Safe file size calculation

    Args:
        file: werkzeug FileStorage object

    Returns:
        int: File size in bytes
    """
    try:
        if file:
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
            return file_size
        return 0
    except Exception:
        return 0