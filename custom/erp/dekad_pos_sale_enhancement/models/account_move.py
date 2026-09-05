from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    partner_contact = fields.Char(string='Contact Phone', compute='_compute_partner_contact', store=True , search='_search_partner_contact')

    def _get_ar_lang_installed(self):
        """Check if a specific language is installed in the system."""
        return bool(self.env['res.lang'].search([('code', '=', 'ar_001')], limit=1))

    @api.depends('partner_id.phone', 'partner_id.mobile')
    def _compute_partner_contact(self):
        for record in self:
            phone = record.partner_id.phone
            mobile = record.partner_id.mobile

            if phone and mobile and phone != mobile:
                record.partner_contact = f"{phone} / {mobile}"
            else:
                record.partner_contact = phone or mobile or ''

    @api.model
    def _search_partner_contact(self, operator, value):
        return [
            '|',
            ('partner_id.phone', operator, value),
            ('partner_id.mobile', operator, value)
        ]

    def action_send_whatsapp(self):
        """Open WhatsApp wizard from Invoice"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "send.whatsapp.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_invoice_id": self.id,
                "default_template_id": self.env.ref("dekad_pos_sale_enhancement.whatsapp_invoice_template").id,

            },
        }
