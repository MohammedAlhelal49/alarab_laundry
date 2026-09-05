from odoo import fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = "base.document.layout"

    show_report_signature = fields.Boolean(
        string="Show Signature Section",
        related="company_id.show_report_signature",
        readonly=False,
    )

    def document_layout_save(self):
        self.ensure_one()

        self.company_id.show_report_signature = self.show_report_signature

        return super().document_layout_save()