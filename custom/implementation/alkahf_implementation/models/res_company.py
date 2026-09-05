# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
import re
from odoo import api, fields, models,_
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.tools.translate import _



class ResCompanyInherited(models.Model):
    _inherit = 'res.company'

    company_code = fields.Char(string="Company Code")
    po_box = fields.Char(string="P.O. Box")
    tax_invoice_terms = fields.Html(string="Tax Invoice Terms & Conditions",)
    sale_commitment_declaration = fields.Html(
        string="Commitment & Declaration Terms"
    )
    company_header = fields.Binary(string="Company Header")
    watermark_photo = fields.Binary(string="Watermark Photo")
    move_serial_prefix = fields.Char(
        string='Journal Serial Prefix',
        default='JV'
    )
    name_en = fields.Char(
        string='Company Name (English)'
    )
    
    enable_sale_cost_validation = fields.Boolean(
        string="Validate Sale Price Against Cost"
    )

    def write(self, vals):
        res = super().write(vals)

        if 'move_serial_prefix' in vals:

            for company in self:

                posted_moves = self.env['account.move'].search([
                    ('company_id', '=', company.id),
                    ('state', '=', 'posted'),
                    ('serial_number', '!=', False),
                ], order='date asc, id asc')

                for move in posted_moves:
                    try:
                        number = move.serial_number.split('/')[-1]
                    except Exception:
                        continue

                    move.serial_number = (
                        f"{company.move_serial_prefix}/{number}"
                    )

        return res


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    company_code = fields.Char(string="Company Code", related="company_id.company_code", readonly=False)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tax_invoice_terms = fields.Html(
        related='company_id.tax_invoice_terms',
        string="Tax Invoice Terms & Conditions",
        readonly=False,
    )

    sale_commitment_declaration = fields.Html(
        related='company_id.sale_commitment_declaration',
        string="Commitment & Declaration Terms",
        readonly=False
    )

    enable_sale_cost_validation = fields.Boolean(
        related='company_id.enable_sale_cost_validation',
        readonly=False
    )

