import re
import urllib.parse
import phonenumbers
from odoo import models, fields, api
from odoo.exceptions import UserError

class SendWhatsappWizard(models.TransientModel):
    _inherit = "send.whatsapp.wizard"


    sale_order_id = fields.Many2one("sale.order", string="Quotation")
    invoice_id = fields.Many2one("account.move", string="Invoice")
    pos_order_id = fields.Many2one("pos.order", string="POS Order")

    @api.onchange("template_id")
    def _onchange_template(self):
        if self.template_id and self.partner_id:
            extra = {}

            # Add quotation details if available
            if self.sale_order_id:
                base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                link = self.sale_order_id.get_portal_url()
                extra["quotation_link"] = base_url + link
                extra["quotation_name"] = self.sale_order_id.name
                extra["quotation_amount"] = f"{self.sale_order_id.currency_id.symbol} {self.sale_order_id.amount_total:,.2f}"

            # Add invoice details if available
            if self.invoice_id:
                base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                link = self.invoice_id.get_portal_url()  # Get the portal URL for the invoice
                extra["invoice_link"] = base_url + link
                extra["invoice_name"] = self.invoice_id.name
                extra["invoice_amount"] = f"{self.invoice_id.amount_total:,.2f} {self.invoice_id.currency_id.symbol} "


            if self.pos_order_id:
                extra["pos_order_name"] = self.pos_order_id.name
                extra["pos_order_amount"] = (
                    f"{self.pos_order_id.amount_total:,.2f} "
                    f"{self.pos_order_id.currency_id.symbol}"
                )


            # Render the message with both quotation and invoice details
            self.preview_message = self.env["whatsapp.template"].render_template(
                self.template_id.message, self.partner_id, extra_context=extra
            )

    def action_open_whatsapp(self):
        self.ensure_one()
        phone = self.partner_id.mobile or self.partner_id.phone
        if not phone:
            raise UserError("No phone number found for this partner.")

        number = phonenumbers.parse(phone, 'DE')  # Default country
        phone = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)

        # Always rebuild the message with context
        extra = {}
        if self.sale_order_id:
            base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            link = self.sale_order_id.get_portal_url()
            extra["quotation_link"] = base_url + link
            extra["quotation_name"] = self.sale_order_id.name
            extra["quotation_amount"] = f" {self.sale_order_id.amount_total:,.2f} {self.sale_order_id.currency_id.symbol}"

        if self.invoice_id:
            base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            link = self.invoice_id.get_portal_url()
            extra["invoice_link"] = base_url + link
            extra["invoice_name"] = self.invoice_id.name
            extra["invoice_amount"] = f" {self.invoice_id.amount_total:,.2f} {self.invoice_id.currency_id.symbol}"

        if self.pos_order_id:
            extra["pos_order_name"] = self.pos_order_id.name
            extra["pos_order_amount"] = (
                f"{self.pos_order_id.amount_total:,.2f} "
                f"{self.pos_order_id.currency_id.symbol}"
            )


        # Render the message with the updated context
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