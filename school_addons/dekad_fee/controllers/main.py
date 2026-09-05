from odoo import _
from odoo.http import route, request
from odoo.addons.portal.controllers import portal
from werkzeug.utils import redirect
from odoo.exceptions import AccessError, MissingError
import base64


class FeeWebsite(portal.CustomerPortal):

    @route(
        ["/student/fees", "/student/fees/page/<int:page>", "/student/fees/<int:id>",
         "/student/fees/<int:id>/page/<int:page>"],
        auth="user",
        website=True,
    )
    def fees(self, date_begin=None, date_end=None, sortby='date_new', page=1, **kwargs):
        parent_student_param = kwargs.get("id")
        user = request.env.user

        # Security Check: Verify parent access to student
        if user.is_parent and parent_student_param:
            parent_record = request.env['de.parent'].sudo().search([('user_id', '=', user.id)])
            if not parent_record or int(parent_student_param) not in parent_record.student_ids.ids:
                request.session['error_message'] = 'Access denied: You can only view your own children\'s information.'
                return redirect('/my/students')

        # Check general redirect conditions
        if helper.redirect_portal_page(parent_student_param):
            return redirect(helper.redirect_portal_page(parent_student_param))

        # Define domain based on user type
        if parent_student_param:
            # parent viewing specific student
            domain = [('student_id', '=', int(parent_student_param))]
        else:
            # student viewing their own fees
            current_student = request.env['de.student'].sudo().search([('user_id', '=', user.id)])
            domain = [('student_id', '=', current_student.id)] if current_student else []

        student_fee_env = request.env["de.student.fee"]
        searchbar_sorts = {
            'date_new': {'label': _('Newest'), 'order': 'create_date desc'},
            'date_old': {'label': _('Oldest'), 'order': 'create_date'},
            'grade': {'label': _('Grade'), 'order': 'grade_id'},
            'amount': {'label': _('Amount'), 'order': 'amount desc'},
            'status': {'label': _('Status'), 'order': 'state'},
        }

        if not sortby:
            sortby = 'date_new'
        order = searchbar_sorts[sortby]['order']

        # Prepare pager data
        student_fee_count = student_fee_env.sudo().search_count(domain)
        page_url = f"/student/fees/{parent_student_param}" if parent_student_param else "/student/fees"
        pager_data = portal.pager(
            url=page_url,
            total=student_fee_count,
            page=page,
            step=self._items_per_page,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby}
        )

        # Recordset according to pager and domain filter
        student_fee = student_fee_env.sudo().search(
            domain, order=order, limit=self._items_per_page, offset=pager_data["offset"]
        )
        if user.is_parent and parent_student_param:
            for fee in student_fee:
                if fee.invoice_id and not fee.invoice_id.access_token:
                    fee.invoice_id.sudo()._portal_ensure_token()
        # Prepare template values
        values = self._prepare_portal_layout_values()
        values.update({
            "fee_records": student_fee,
            "default_url": page_url,
            "page_url": page_url,
            "pager": pager_data,
            'date': date_begin,
            'date_end': date_end,
            'searchbar_sortings': searchbar_sorts,
            'sortby': sortby,
            'parent_student_param': parent_student_param,
            'student': helper.get_student(parent_student_param),
            "page_name": "Fees",
            "home_url": f"/my/home/{parent_student_param}" if parent_student_param else "/my/home"
        })



        return request.render("dekad_fee.student_fee", values)

    @route(['/student/fees/<int:fee_id>/invoice'], type='http', auth="user", website=True)
    def view_fee_invoice(self, fee_id, **kwargs):
        """View invoice details for a specific fee"""
        parent_student_param = kwargs.get("id")
        user = request.env.user

        # Get the fee record
        fee = request.env['de.student.fee'].sudo().browse(fee_id)
        if not fee.exists():
            return request.render('website.404')

        # Security check
        if not self._check_fee_access(fee, user, parent_student_param):
            request.session['error_message'] = 'Access denied: You can only view your own fees/invoices.'
            return redirect('/student/fees')

        # Check if invoice exists
        if not fee.invoice_id:
            request.session['error_message'] = 'No invoice has been created for this fee yet.'
            return redirect('/student/fees')

        # Ensure invoice has portal token
        if not fee.invoice_id.access_token:
            fee.invoice_id._portal_ensure_token()

        values = {
            'fee': fee,
            'invoice': fee.invoice_id,
            'parent_student_param': parent_student_param,
            'student': fee.student_id,
            'page_name': 'Invoice Details',
            'home_url': f"/my/home/{parent_student_param}" if parent_student_param else "/my/home",
            'back_url': f"/student/fees/{parent_student_param}" if parent_student_param else "/student/fees"
        }

        return request.render("dekad_fee.invoice_detail", values)

    @route(['/student/fees/<int:fee_id>/invoice/download'], type='http', auth="user", website=True)
    def download_fee_invoice(self, fee_id, **kwargs):
        """Download invoice PDF for a specific fee"""
        parent_student_param = kwargs.get("id")
        user = request.env.user

        # Get the fee record
        fee = request.env['de.student.fee'].sudo().browse(fee_id)
        if not fee.exists():
            return request.render('website.404')

        # Security check
        if not self._check_fee_access(fee, user, parent_student_param):
            request.session['error_message'] = 'Access denied: You can only download your own invoices.'
            return redirect('/student/fees')

        # Check if invoice exists
        if not fee.invoice_id:
            request.session['error_message'] = 'No invoice has been created for this fee yet.'
            return redirect('/student/fees')

        # Generate PDF report
        try:
            report = request.env.ref('account.account_invoices')
            if not report:
                # Try alternative report reference
                report = request.env.ref('account.action_report_invoice')

            pdf_content, _ = report.sudo()._render_qweb_pdf([fee.invoice_id.id])

            # Prepare filename
            invoice_name = fee.invoice_id.name or f"Invoice-{fee_id}"
            filename = f"{invoice_name.replace('/', '-')}.pdf"

            # Return PDF response
            pdf_headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf_content)),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]

            return request.make_response(pdf_content, headers=pdf_headers)

        except Exception as e:
            request.session['error_message'] = f'Error generating PDF: {str(e)}'
            return redirect(f'/student/fees/{fee_id}/invoice')

    @route(['/student/fees/<int:fee_id>/invoice/print'], type='http', auth="user", website=True)
    def print_fee_invoice(self, fee_id, **kwargs):
        """Print/view invoice PDF in browser for a specific fee"""
        parent_student_param = kwargs.get("id")
        user = request.env.user

        # Get the fee record
        fee = request.env['de.student.fee'].sudo().browse(fee_id)
        if not fee.exists():
            return request.render('website.404')

        # Security check
        if not self._check_fee_access(fee, user, parent_student_param):
            request.session['error_message'] = 'Access denied: You can only view your own invoices.'
            return redirect('/student/fees')

        # Check if invoice exists
        if not fee.invoice_id:
            request.session['error_message'] = 'No invoice has been created for this fee yet.'
            return redirect('/student/fees')

        # Generate PDF report for viewing
        try:
            report = request.env.ref('account.account_invoices')
            if not report:
                report = request.env.ref('account.action_report_invoice')

            pdf_content, _ = report.sudo()._render_qweb_pdf([fee.invoice_id.id])

            # Return PDF for inline viewing
            pdf_headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf_content)),
            ]

            return request.make_response(pdf_content, headers=pdf_headers)

        except Exception as e:
            request.session['error_message'] = f'Error generating PDF: {str(e)}'
            return redirect(f'/student/fees/{fee_id}/invoice')

    @route(['/student/fees/<int:fee_id>/pay'], type='http', auth="user", website=True)
    def pay_fee_invoice(self, fee_id, **kwargs):
        """Redirect to payment for invoice (if payment module is available)"""
        parent_student_param = kwargs.get("id")
        user = request.env.user

        # Get the fee record
        fee = request.env['de.student.fee'].sudo().browse(fee_id)
        if not fee.exists():
            return request.render('website.404')

        # Security check
        if not self._check_fee_access(fee, user, parent_student_param):
            request.session['error_message'] = 'Access denied: You can only pay your own fees.'
            return redirect('/student/fees')

        # Check if invoice exists
        if not fee.invoice_id:
            request.session['error_message'] = 'No invoice has been created for this fee yet.'
            return redirect('/student/fees')

        # Check if already paid
        if fee.invoice_id.payment_state == 'paid':
            request.session['info_message'] = 'This invoice has already been paid.'
            return redirect(f'/student/fees/{fee_id}/invoice')

        # Redirect to invoice portal page for payment
        if fee.invoice_id.access_token:
            return redirect(f'/my/invoices/{fee.invoice_id.id}?access_token={fee.invoice_id.access_token}')
        else:
            # Ensure invoice has token
            fee.invoice_id._portal_ensure_token()
            return redirect(f'/my/invoices/{fee.invoice_id.id}?access_token={fee.invoice_id.access_token}')

    def _check_fee_access(self, fee, user, parent_student_param=None):
        """Check if user has access to this fee"""
        # If parent is viewing specific student
        if user.is_parent and parent_student_param:
            parent_record = request.env['de.parent'].sudo().search([('user_id', '=', user.id)])
            if (parent_record and
                    int(parent_student_param) in parent_record.student_ids.ids and
                    fee.student_id.id == int(parent_student_param)):
                return True

        # If student is viewing their own fees
        elif not user.is_parent:
            current_student = request.env['de.student'].sudo().search([('user_id', '=', user.id)])
            if current_student and fee.student_id.id == current_student.id:
                return True

        return False

    def _prepare_home_portal_values(self, counters):
        """Add fee counters to portal home"""
        values = super()._prepare_home_portal_values(counters)

        user = request.env.user

        if 'fee_count' in counters:
            if user.is_parent:
                # Count fees for all children
                parent_record = request.env['de.parent'].sudo().search([('user_id', '=', user.id)])
                if parent_record:
                    fee_count = request.env['de.student.fee'].sudo().search_count([
                        ('student_id', 'in', parent_record.student_ids.ids)
                    ])
                else:
                    fee_count = 0
            else:
                # Count fees for student
                current_student = request.env['de.student'].sudo().search([('user_id', '=', user.id)])
                fee_count = request.env['de.student.fee'].sudo().search_count([
                    ('student_id', '=', current_student.id)
                ]) if current_student else 0

            values['fee_count'] = fee_count

        if 'invoice_count' in counters:
            if user.is_parent:
                parent_record = request.env['de.parent'].sudo().search([('user_id', '=', user.id)])
                if parent_record:
                    invoice_count = request.env['de.student.fee'].sudo().search_count([
                        ('student_id', 'in', parent_record.student_ids.ids),
                        ('invoice_id', '!=', False)
                    ])
                else:
                    invoice_count = 0
            else:
                current_student = request.env['de.student'].sudo().search([('user_id', '=', user.id)])
                invoice_count = request.env['de.student.fee'].sudo().search_count([
                    ('student_id', '=', current_student.id),
                    ('invoice_id', '!=', False)
                ]) if current_student else 0

            values['invoice_count'] = invoice_count

        return values

    def _check_invoice_access_token(self, fee_record, user):
        """Ensure invoice has access token for portal access"""
        if fee_record.invoice_id and not fee_record.invoice_id.access_token:
            fee_record.invoice_id.sudo()._portal_ensure_token()
        return fee_record.invoice_id.access_token if fee_record.invoice_id else None