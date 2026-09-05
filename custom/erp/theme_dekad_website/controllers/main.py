# controllers/main.py
from odoo import http, fields
from odoo.http import request
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class DemoRequestController(http.Controller):

    def _schedule_task_activities(self, task, note):
        """Assign activities to configured users on the new task."""
        company = task.company_id or request.website.sudo().company_id
        target_users = company.website_lead_activity_user_ids

        if not target_users:
            main_company = request.env['res.company'].sudo().browse(1)
            target_users = main_company.website_lead_activity_user_ids

        if not target_users:
            return

        activity_type = request.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        model_id = request.env['ir.model'].sudo().search([('model', '=', 'project.task')], limit=1).id

        for user in target_users:
            request.env['mail.activity'].sudo().create({
                'res_model_id': model_id,
                'res_id': task.id,
                'activity_type_id': activity_type.id if activity_type else 1,
                'summary': 'Follow up: New Website Request',
                'note': note,
                'user_id': user.id,
                'date_deadline': fields.Date.today(),
            })

    def _create_request_task(self, post, request_type):
        """Helper to process form data and create the project task."""
        prefix = "DEMO" if request_type == 'demo' else "CONSULTATION"
        task_name = f"{prefix}: {post.get('name')} ({post.get('company_name')})"

        # Identify which date field to look for in the POST data
        date_key = 'dekad_demo_date' if request_type == 'demo' else 'dekad_consultation_date'
        date_str = post.get(date_key)
        date_val = False

        if date_str:
            try:
                # Basic cleaning for Odoo datetime format
                date_val = date_str.replace('T', ' ')
                if len(date_val) == 16:
                    date_val += ':00'
            except Exception as e:
                _logger.warning("Could not parse date %s: %s", date_str, e)

        emp_str = post.get('employees')
        employees_val = int(emp_str) if emp_str and emp_str.isdigit() else 0

        task_vals = {
            'name': task_name,
            'dekad_contact_name': post.get('name'),
            'dekad_company_name': post.get('company_name'),
            'dekad_email': post.get('email'),
            'dekad_phone': post.get('phone'),
            'dekad_request_type': post.get('type_label'),
            'dekad_industry': post.get('industry', ''),
            'dekad_employees': employees_val,
            'dekad_demo_date': date_val,
            'description': f"A new {request_type} has been requested from the website.",
        }

        new_task = request.env['project.task'].sudo().create(task_vals)
        new_task.sudo().message_post(body=f"System: New {request_type.capitalize()} Request submitted.")

        self._schedule_task_activities(
            new_task,
            note=f"A new {request_type} request has arrived. Review the task and convert to Lead when ready."
        )
        return new_task

    def _validate_recaptcha(self, post):
        """Helper to validate Google reCAPTCHA v3 token via Odoo's native checker."""
        token = post.get('recaptcha_token_response')
        # Check if reCAPTCHA is active and validate the token
        if hasattr(request.website, 'is_captcha_valid'):
            return request.website.is_captcha_valid(token)
        return True  # Fallback if captcha is disabled in settings

    # --- ROUTES ---

    @http.route('/request-demo', type='http', auth='public', website=True)
    def request_demo_page(self, **kw):
        return request.render('theme_dekad_website.request_demo_form_template', kw)

    @http.route('/request-demo/submit', type='http', auth='public', website=True, methods=['POST'])
    def request_demo_submit(self, **post):
        # 1. Validate reCAPTCHA before doing anything else
        if not self._validate_recaptcha(post):
            post['error'] = 'Invalid reCAPTCHA. Please refresh the page and try again.'
            return request.render('theme_dekad_website.request_demo_form_template', post)

        # 2. Process form if validation passes
        self._create_request_task(post, 'demo')
        return request.render('theme_dekad_website.request_demo_success_template', {})

    @http.route('/free-consultation', type='http', auth='public', website=True)
    def request_consultation_page(self, **kw):
        return request.render('theme_dekad_website.request_consultation_form_template', kw)

    @http.route('/free-consultation/submit', type='http', auth='public', website=True, methods=['POST'])
    def request_consultation_submit(self, **post):
        # 1. Validate reCAPTCHA
        if not self._validate_recaptcha(post):
            post['error'] = 'Invalid reCAPTCHA. Please refresh the page and try again.'
            return request.render('theme_dekad_website.request_consultation_form_template', post)

        # 2. Process form if validation passes
        self._create_request_task(post, 'consultation')
        return request.render('theme_dekad_website.request_consultation_success_template', {})


class DebugController(http.Controller):

    @http.route('/test-500', type='http', auth='public', website=True, sitemap=False)
    def trigger_error(self):
        try:
            bad_calculation = 10 / 0
            return request.render('website.homepage')

        except Exception as core_error:
            _logger.error("Production Error caught by handler: %s", str(core_error), exc_info=True)

            try:
                # Target the fresh v2 layout
                response = request.render('theme_dekad_website.custom_500_page_v2', {})
                response.status_code = 500
                return response
            except Exception as qweb_error:
                return request.make_response(
                    f"QWEB TEMPLATE CRASH DETECTED: {str(qweb_error)}",
                    headers=[('Content-Type', 'text/plain')],
                    status=500
                )