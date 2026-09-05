from markupsafe import Markup

from odoo import models  ,fields


class BaseDocumentLayoutInherited(models.TransientModel):
    _inherit = 'base.document.layout'


    def get_base_report_footer(self):
        company = self.env.company
        footer_fields = [field for field in [company.phone, company.email, company.website, company.vat] if
                         isinstance(field, str) and len(field) > 0]
        return Markup(' ').join(footer_fields)

    def reset_layout(self):
        self.env.company.font = "Lato"
        self.env.company.layout_background = "Blank"
        self.env.company.report_header = ""
        self.env.company.company_details = ""
        self.env.company.report_footer = self.get_base_report_footer()
        self.env.company.paperformat_id = self.env.ref('base.paperformat_euro').id
        self.primary_color = self.logo_primary_color
        self.secondary_color = self.logo_secondary_color
        action = self.env.ref('web.action_base_document_layout_configurator')
        return action.read()[0]
