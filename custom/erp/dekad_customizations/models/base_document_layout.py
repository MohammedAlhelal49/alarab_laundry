# -*- coding: utf-8 -*-

from odoo import api, fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    header_image = fields.Binary(
        related="company_id.header_image",
        readonly=False,
        string="Header Image",
    )

    footer_image = fields.Binary(
        related="company_id.footer_image",
        readonly=False,
        string="Footer Image",
    )

    @api.depends(
        "report_layout_id",
        "logo",
        "font",
        "primary_color",
        "secondary_color",
        "report_header",
        "report_footer",
        "layout_background",
        "layout_background_image",
        "company_details",
        "header_image",
        "footer_image",
    )
    def _compute_preview(self):
        return super()._compute_preview()

    @api.onchange("company_id")
    def _onchange_company_id_header_footer(self):
        for wizard in self:
            wizard.header_image = wizard.company_id.header_image
            wizard.footer_image = wizard.company_id.footer_image

    def _get_bilingual_report_company(self):
        self.ensure_one()
        return self.company_id