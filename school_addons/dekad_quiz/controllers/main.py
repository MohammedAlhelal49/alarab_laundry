from odoo import http, _
from odoo.http import route, request, Response
from odoo.addons.portal.controllers import portal
import base64, json
from werkzeug.utils import redirect
from odoo.exceptions import AccessError


def get_quiz_page_url(key, parent_student_param=None, id=None):
    if key == "list":
        return f"/student/quizzes/{parent_student_param}" if parent_student_param else "/student/quizzes"
    elif key == "show":
        return f"/student/quiz/{id}?parent_student_param={parent_student_param}" if parent_student_param else f"/student/quiz/{id}"
    elif key == "home":
        return f"/my/home/{parent_student_param}" if parent_student_param else "/my/home"


def get_quiz_submission_page_url(key, parent_student_param=None, id=None):
    if key == "show":  # show or create (conditions)
        return f"/student/quiz/{id}/submission/?parent_student_param={parent_student_param}" if parent_student_param else f"/student/quiz/{id}/submission"
    elif key == "home":
        return f"/my/home/{parent_student_param}" if parent_student_param else "/my/home"
    elif key == "update":
        return f"/student/quiz/submission/update/{id}?parent_student_param={parent_student_param}" if parent_student_param else f"/student/quiz/submission/update/{id}"


class QuizWebsite(portal.CustomerPortal):
    @route(
        ["/student/quizzes", "/student/quizzes/<int:id>", "/student/quizzes/<int:id>/page/<int:page>",
         "/student/quizzes/page/<int:page>"],
        auth="user",
        website=True,
    )
    def quizzes(self, date_begin=None, date_end=None, filterby=None, sortby='date_new', page=1, search='',
                search_in='name', **kwargs):
        parent_student_param = kwargs.get("id")

        # SECURITY: Check if parent has access to this specific student
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # Redirect check
        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        # FIXED: Proper domain construction for quizzes (excluding drafts)
        if parent_student_param:
            # For parents viewing specific student - use sudo() for database access
            domain = [('student_ids', 'in', [int(parent_student_param)]), ('state', '!=', 'draft')]
            use_sudo = True
            print(f"Parent domain: {domain}")
        else:
            # For students viewing their own quizzes
            current_student = request.env['de.student'].search([('user_id', '=', request.env.user.id)])
            if current_student:
                domain = [('student_ids', 'in', [current_student.id]), ('state', '!=', 'draft')]
                use_sudo = False
            else:
                domain = [('id', '=', False)]  # No quizzes if no student found
                use_sudo = False
            print(f"Student domain: {domain}")

        student_quiz_env = request.env["de.quiz"]
        if use_sudo:
            student_quiz_env = student_quiz_env.sudo()

        searchbar_sorts = {
            'date_new': {'label': _('Newest'), 'order': 'create_date DESC'},
            'date_old': {'label': _('Oldest'), 'order': 'create_date'},
            'type': {'label': _('Type'), 'order': 'type_id'},
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
        print(f"Final domain: {final_domain}")

        # Get count and records with proper permissions
        student_quiz_count = student_quiz_env.search_count(final_domain)
        print(f"Quiz count: {student_quiz_count}")

        # Prepare pager data
        page_url = get_quiz_page_url('list', parent_student_param)
        pager_data = portal.pager(
            url=page_url,
            total=student_quiz_count,
            page=page,
            step=self._items_per_page,
            url_args={'date_begin': date_begin,
                      'date_end': date_end, 'sortby': sortby, 'search': search, 'search_in': search_in,
                      'filterby': filterby, }
        )

        # Get quiz records with proper permissions
        student_quiz = student_quiz_env.search(
            final_domain, order=order, limit=self._items_per_page, offset=pager_data["offset"]
        )

        print(f"Found quiz records: {len(student_quiz)}")

        # Prepare template values
        values = self._prepare_portal_layout_values()

        quiz_submission_list = []
        for quiz in student_quiz:
            # FIXED: Get proper student ID for submission check
            student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)

            data_object = {
                'id': quiz.id,
                'has_draft_submission': request.env['de.quiz.submission'].sudo().search_count(
                    [('student_id', '=', student_id), ('quiz_id', '=', quiz.id),
                     ('state', '=', 'draft')])
            }
            quiz_submission_list.append(data_object)

        values.update({
            "quiz_records": student_quiz,
            "quiz_submission_list": quiz_submission_list,
            "page_name": "Quizzes",
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
            "home_url": get_quiz_page_url('home', parent_student_param),
            "parent_student_param": parent_student_param,
            'student': helper.get_student(parent_student_param)
        })

        return request.render("dekad_quiz.student_quiz", values)

    @route("/student/quiz/<model('de.quiz'):record>", auth='user', website=True)
    def quiz_show(self, record, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')

        # SECURITY: Check if parent has access to this specific student
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # SECURITY: Check if quiz belongs to the student
        student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)
        if student_id not in record.student_ids.ids:
            raise AccessError(_("This quiz is not assigned to the specified student."))

        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        model_attachment = {
            "model": "de.quiz",
            "field": "file",
            "id": record.id,
        }
        data_object = helper.get_file_attachment_type(model_attachment)
        file_name = record.file_name
        # file_type = data_object['file_type']

        return http.request.render('dekad_quiz.student_quiz_show', {
            'page_name': 'Quiz Show',
            "home_url": get_quiz_page_url('home', parent_student_param),
            "list_url": get_quiz_page_url('list', parent_student_param),
            "page_url": get_quiz_page_url('show', parent_student_param, record.id),
            "record": record,
            "parent_student_param": parent_student_param,
            'student': helper.get_student(parent_student_param),
            'file_name': f"{file_name}" if data_object['attachment'] else "",
        })

    @route('/student/quiz/download/<model("de.quiz"):record>', type='http', auth="user")
    def quiz_download(self, record, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')

        # SECURITY: Check if parent has access to this specific student
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # SECURITY: Check if quiz belongs to the student
        student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)
        if student_id not in record.student_ids.ids:
            raise AccessError(_("This quiz is not assigned to the specified student."))

        data_object = {
            'model': 'de.quiz',
            'field': 'file',
            'id': record.id
        }
        file_object = helper.get_file_attachment_type(data_object)

        file = base64.b64decode(record.file)
        headers = [
            ('Content-Type', file_object["attachment"].mimetype),
            ('Content-Disposition', f'attachment; filename="{record.file_name}"')
        ]
        return request.make_response(file, headers=headers)

    # handling the submission section
    @route(["/student/quiz/<model('de.quiz'):quiz>/submission"], auth="user", website=True)
    def quiz_submission(self, quiz=None, **kwargs):
        parent_student_param = kwargs.get('parent_student_param')

        # SECURITY: Check if parent has access to this specific student
        if parent_student_param and not helper.check_parent_student(parent_student_param):
            raise AccessError(_("You don't have permission to access this student's information."))

        # SECURITY: Check if quiz belongs to the student
        student_id = int(parent_student_param) if parent_student_param else helper.get_student_id(None)
        if student_id not in quiz.student_ids.ids:
            raise AccessError(_("This quiz is not assigned to the specified student."))

        # Get the correct student record
        if parent_student_param:
            student = request.env['de.student'].sudo().browse(int(parent_student_param))
        else:
            student = request.env['de.student'].search([('user_id', '=', request.uid)])

        # creating the open without submit record
        attempt_count = request.env["de.quiz.submission.attempt"].sudo().search_count(
            [('quiz_id', '=', quiz.id), ('student_id', '=', student.id)])

        data_object = {}
        data_object['student_id'] = student.id
        data_object['quiz_id'] = quiz.id
        data_object['name'] = f"Attempt ({attempt_count + 1})"

        # FIXED: Get submission for specific student
        submission = request.env['de.quiz.submission'].sudo().search([
            ('quiz_id', '=', quiz.id),
            ('student_id', '=', student.id)
        ], limit=1)

        if attempt_count < 2 and not submission:
            request.env["de.quiz.submission.attempt"].sudo().create(data_object)

        attempts = request.env["de.quiz.submission.attempt"].sudo().search(
            [('quiz_id', '=', quiz.id), ('student_id', '=', student.id)])

        has_draft_submission = request.env['de.quiz.submission'].sudo().search_count(
            [('student_id', '=', student.id), ('quiz_id', '=', quiz.id),
             ('state', '=', 'draft')])

        if has_draft_submission:
            return redirect(get_quiz_page_url('list', parent_student_param))

        return http.request.render('dekad_quiz.student_quiz_submission', {
            'page_name': 'Quiz Submission',
            "quiz_list_url": get_quiz_page_url('list', parent_student_param),
            "quiz_show_url": get_quiz_page_url('show', parent_student_param, quiz.id),
            "home_url": get_quiz_submission_page_url('home', parent_student_param),
            "page_url": get_quiz_submission_page_url('show', parent_student_param, quiz.id),
            "quiz": quiz,
            'submission': submission,
            'attempts': attempts,
            'submitted_date': submission.create_date.strftime('%Y-%m-%d %H:%M:%S') if submission else None,
            'student': helper.get_student(parent_student_param),
            "parent_student_param": parent_student_param,
        })

    @route('/student/quizzes/submission/create', auth='user', website=True, methods=['POST'])
    def quiz_submission_create(self, **kwargs):
        # Note: This method should only be accessible by students, not parents
        # Parents should only have read-only access to quiz submissions
        quiz = request.env['de.quiz'].browse(int(kwargs.get('quiz_id')))
        data_object = {}
        data_object['student_id'] = request.env['de.student'].search([('user_id', '=', request.uid)]).id
        data_object['quiz_id'] = int(kwargs.get('quiz_id'))
        data_object['state'] = 'finish' if quiz.correction_type == 'automatic' else 'correcting'

        submission = request.env["de.quiz.submission"].create(data_object)
        submission.answer_ids.unlink()

        data_list = []
        for question in quiz.question_ids:
            answer = {'submission_id': submission.id, 'question_id': question.id,
                      'answer': kwargs.get(f'question_{question.id}')}
            data_list.append(answer)
        request.env['de.quiz.submission.answer'].create(data_list)
        return redirect(f"/student/quiz/{kwargs.get('quiz_id')}/submission")

    @http.route(['/student/quiz/get'], auth="user", type="http", csrf=False)
    def get_quiz_data(self, **kwargs):
        if kwargs.get('quiz_id'):
            quiz = request.env['de.quiz'].browse(int(kwargs.get('quiz_id')))
            data = dict()
            data['id'] = quiz.id
            data['hour_limit'] = quiz.hour_limit
            data['minute_limit'] = quiz.minute_limit
            return Response(json.dumps(data, default=str), content_type='application/json;charset=utf-8',
                            status=200)
        return False