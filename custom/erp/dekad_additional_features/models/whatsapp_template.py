import re
import phonenumbers
from odoo import models, fields, api

class WhatsappTemplate(models.Model):
    _name = "whatsapp.template"
    _description = "WhatsApp Message Template"

    name = fields.Char("Template Name", required=True)
    message = fields.Text(
        "Message",
        required=True,
        help="You can use placeholders like {{partner_name}} or {{invoice_name}}"
    )

    @api.model
    def render_template(self, template_text, partner, extra_context=None):
        """Replace placeholders with real values"""
        context = {
            "partner_name": partner.name or "",
            "partner_phone": partner.mobile or partner.phone or "",
            "email": partner.email or "",
        }
        if extra_context:
            context.update(extra_context)
        msg = template_text
        for key, value in context.items():
            msg = msg.replace("{{%s}}" % key, str(value))
        return msg


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_send_whatsapp(self):
        """Wizard-like selection of template"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "send.whatsapp.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_partner_id": self.id},
        }

