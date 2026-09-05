import re
import urllib.parse
import phonenumbers
from odoo import models, fields, api
from odoo.exceptions import UserError

class SendWhatsappWizard(models.TransientModel):
    _name = "send.whatsapp.wizard"
    _description = "Send WhatsApp Wizard"

    partner_id = fields.Many2one("res.partner", required=True)
    template_id = fields.Many2one("whatsapp.template", string="Template", required=True)
    preview_message = fields.Text("Preview", readonly=True) # Add the invoice reference

    @api.onchange("template_id")
    def _onchange_template(self):
        if self.template_id and self.partner_id:
            extra = {}

            # Render the message with both quotation and invoice details
            self.preview_message = self.env["whatsapp.template"].render_template(
                self.template_id.message, self.partner_id, extra_context=extra
            )

    def action_open_whatsapp(self):
        self.ensure_one()
        phone = self.partner_id.mobile or self.partner_id.phone
        if not phone:
            raise UserError("No phone number found for this partner.")

        try:
            # Use partner country code or fallback to 'AE'
            region = self.partner_id.country_id.code or 'AE'
            number = phonenumbers.parse(phone, region)
            if not phonenumbers.is_valid_number(number):
                raise UserError("The phone number is not valid.")
            phone = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
            phone = phone.replace("+", "")  # Remove '+' for WhatsApp URL
        except phonenumbers.NumberParseException:
            raise UserError("Invalid phone number format.")

        # Render message
        extra = {}
        msg = self.env["whatsapp.template"].render_template(
            self.template_id.message, self.partner_id, extra_context=extra
        )

        text = urllib.parse.quote(msg or "", safe=":/?&=.-_")
        url = f"https://web.whatsapp.com/send?phone={phone}&text={text}"

        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }
