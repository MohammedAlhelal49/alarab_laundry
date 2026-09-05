import io
from odoo import models
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter, to_pdf_stream


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # OVERRIDE
        res = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)
        report = self._get_report(report_ref)
        if not res_ids or report.report_name != 'sh_pdc_followup.report_followup_print_all':
            return res

        options = data.get('options', {})
        for partner_id in res_ids:
            partner = self.env['res.partner'].browse(partner_id)
            join_invoices = options.get('join_invoices', partner.pdc_followup_line_id.join_invoices)
            if not join_invoices:
                continue

            if options.get('attachment_ids'):
                attachments = self.env['ir.attachment'].browse(options.get('attachment_ids'))
            else:
                # pdc.wizard does not inherit mail.thread, so no message_main_attachment_id
                # Look for any PDF attachments linked to the cheque records directly
                cheques = self.env['pdc.wizard'].search([
                    ('partner_id', '=', partner_id),
                    ('payment_type', '=', 'receive_money'),
                    ('state', 'in', ('registered', 'deposited')),
                ])
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', 'pdc.wizard'),
                    ('res_id', 'in', cheques.ids),
                    ('mimetype', '=', 'application/pdf'),
                ])

            if not attachments:
                continue

            writer = OdooPdfFileWriter()
            followup_stream = res[partner_id]['stream']
            input_streams = [followup_stream] + [
                to_pdf_stream(attachment) for attachment in attachments
                if attachment.mimetype == 'application/pdf'
            ]
            for stream in input_streams:
                reader = OdooPdfFileReader(stream, strict=False)
                writer.appendPagesFromReader(reader)

            output_stream = io.BytesIO()
            writer.write(output_stream)
            res[partner_id]['stream'] = output_stream
            for stream in input_streams:
                stream.close()

        return res
