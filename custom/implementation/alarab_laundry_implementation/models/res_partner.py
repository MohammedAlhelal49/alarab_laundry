from odoo import models, api, SUPERUSER_ID
import re


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _format_uae_number(self, phone):
        if not phone:
            return False

        # remove everything except digits
        digits = re.sub(r"\D", "", phone)

        # normalize to UAE
        if digits.startswith("0"):
            digits = "971" + digits[1:]
        elif digits.startswith("971"):
            pass
        else:
            return phone  # skip non-UAE

        # ensure valid length
        if len(digits) != 12:
            return "+" + digits

        return "+{} {} {} {}".format(
            digits[:3],
            digits[3:5],
            digits[5:8],
            digits[8:]
        )

    @api.model
    def _run_mobile_fix(self):
        partners = self.search([
            "|",
            ("phone", "!=", False),
            ("mobile", "!=", False),
        ])

        for p in partners:
            source = p.mobile or p.phone
            formatted = self._format_uae_number(source)

            if formatted and p.mobile != formatted:
                p.write({"mobile": formatted})

    @api.model
    def init(self):
        env = api.Environment(self._cr, SUPERUSER_ID, {})
        env["res.partner"]._run_mobile_fix()