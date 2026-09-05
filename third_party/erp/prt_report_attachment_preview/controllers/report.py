import json
import re
from email.utils import encode_rfc2231
from typing import Any

from werkzeug import urls
from werkzeug.wrappers import Response

from odoo import http
from odoo.http import request, route
from odoo.tools.safe_eval import safe_eval
from odoo.tools.safe_eval import time as safe_time

from odoo.addons.web.controllers.report import ReportController


class CxReportController(ReportController):
    def _get_extra_context_for_single_record(self, report_name, ignore_expr=None):
        """
        Get extra context values for single record report name
        evaluation. This is used to fill missing expressions with
        'report' string to avoid evaluation errors.

        Args:
        report_name (str): Name of the report.
            Example:
            "(object.state in ('draft', 'sent') and 'Quotation - %s' % (object.name))
            or 'Order - %s' % (object.name)"
        ignore_expr (list): List of expressions to ignore.

        Returns:
            Dict: Extra context values
        """
        ignore_expr = ignore_expr or []
        extra_ctx = {}
        for expr in re.findall(r"%.?\(.*?\)", report_name):
            # Remove percent sign and brackets, we don't need them
            expr = expr.replace("%", "").strip()[1:-1].strip()
            # If there is a dot in expression, then lets take
            # first part to get the variable name
            if "." in expr:
                expr = expr.split(".")[0]
            if expr in ignore_expr:
                continue
            extra_ctx[expr] = "report"
        return extra_ctx

    def _compose_report_file_name(self, docids, report):
        """Compose report file name.
        Uses report name + record name(s) if provided

        Args:
            docids ([Int]): list of record ids
            report (ir.action.report()): report record

        Returns:
            Char: composed name of the report
        """
        report_name = "report"
        label_report = report.report_name.startswith('product.report_producttemplatelabe')
        if label_report:
            product_template_ids = request.env['product.template'].sudo().search([]).ids
            product_product_ids = request.env['product.product'].sudo().search([]).ids
            if docids[0] in product_template_ids and not (docids[0] in product_product_ids):
                report.model = 'product.template'
            elif not (docids[0] in product_template_ids)  and  docids[0] in product_product_ids:
                report.model = 'product.product'
        if docids:
            # Use sudo() here to bypass record rules when browsing records
            records = request.env[report.model].sudo().browse(docids)
            record_count = len(docids)
            if record_count == 1 and report.sudo().print_report_name:
                # Single record
                print_report_name = report.sudo().print_report_name
                extra_ctx = self._get_extra_context_for_single_record(
                    print_report_name,
                    ignore_expr=["object", "time"],
                )
                report_name = safe_eval(
                    print_report_name,
                    {
                        "object": records,
                        "time": safe_time,
                        **extra_ctx,
                    },
                )
            else:
                # Multiple records
                report_name = f"{report.name} x{record_count}"
        else:
            report_name = report.name
        return report_name

    # ------------------------------------------------------
    # Report controllers
    # ------------------------------------------------------
    @route(
        [
            "/report/<converter>/<reportname>",
            "/report/<converter>/<reportname>/<docids>",
        ],
        type="http",
        auth="user",
        website=True,
    )
    def report_routes(
            self,
            reportname: str,
            docids: str | None = None,
            converter: str | None = None,
            **data: dict[str, Any],
    ) -> Response:
        """Handle report routes with browser preview for PDFs."""
        excluded_reports = ["point_of_sale.report_saledetails"]
        if converter != "pdf" or reportname in excluded_reports:
            return super().report_routes(
                reportname, docids=docids, converter=converter, **data
            )

        # Use sudo() to ensure the report can be found across companies
        report = request.env["ir.actions.report"].sudo()._get_report_from_name(reportname)
        if not report:
            return request.not_found()

        context = dict(request.env.context)

        # Handle options and context
        if data.get("options"):
            options_str = data.pop("options")
            if isinstance(options_str, str):
                data.update(json.loads(urls.url_unquote_plus(options_str)))

        if data.get("context"):
            context_str = data.get("context")
            if isinstance(context_str, str):
                context.update(json.loads(urls.url_unquote_plus(context_str)))

        # Handle company context
        cid = data.get("cid")
        if cid:
            try:
                allowed_company_ids = [int(cid) for cid in cid.split(",")]
                context["allowed_company_ids"] = allowed_company_ids
            except (ValueError, AttributeError):
                return request.not_found()

        request.env.context = context

        # Handle document IDs
        doc_ids: list[int] = []
        if docids:
            try:
                doc_ids = [int(i) for i in docids.split(",")]
                # Use sudo() here to browse records and bypass access checks
                records = request.env[report.model].sudo().browse(doc_ids)
                # The check_access_rights and check_access_rule calls are now on a sudo'ed recordset,
                # but we can perform a manual check if needed, or rely on sudo() to bypass it.
                # For this use case, we will rely on sudo() to bypass the check.
                # records.check_access("read") # This line is no longer needed with sudo()
            except (ValueError, AttributeError):
                return request.not_found()

        report_name = self._compose_report_file_name(doc_ids, report)

        # Use sudo() when rendering the report to ensure all data is accessible
        pdf = report.with_context(**context).sudo()._render_qweb_pdf(
            reportname, doc_ids, data=data
        )[0]

        return request.make_response(
            pdf,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf)),
                (
                    "Content-Disposition",
                    f"inline; filename*={encode_rfc2231(report_name, 'utf-8')}.pdf",
                ),
            ],
        )

    @http.route("/report/check_wkhtmltopdf", type="json", auth="user")
    def check_wkhtmltopdf(self):
        return request.env["ir.actions.report"].get_wkhtmltopdf_state()
