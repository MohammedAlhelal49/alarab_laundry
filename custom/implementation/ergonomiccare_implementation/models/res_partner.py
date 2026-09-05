from odoo.exceptions import ValidationError
from odoo import models, fields, api, _, SUPERUSER_ID
import re

class ResPartnerInherited(models.Model):
    _inherit = 'res.partner'

    mrn = fields.Char(string='MR No.')
    theqa_no = fields.Char(string='Card No.')
    product_ids = fields.Many2many(
        'product.product',
        'crm_lead_product_rel',
        'lead_id',
        'product_id',
        string='Product')
    product_description = fields.Text(string="Product Description")

    same_name_partner_id = fields.Many2one(
        "res.partner",
        string="Duplicate Name Partner",
        compute="_compute_same_name_partner_id",
        store=True,
    )

    same_contact_partner_id = fields.Many2one(
        "res.partner",
        string="Duplicate Contact Partner",
        compute="_compute_duplicate_partners",
        store=False,
    )

    contact_conflict_label = fields.Char(
        string="Conflict Label",
        compute="_compute_duplicate_partners",
    )

    same_mrn_partner_id = fields.Many2one(
        "res.partner",
        string="Duplicate MRN Partner",
        compute="_compute_duplicate_partners",
        store=False,
    )

    mrn_conflict_label = fields.Char(
        string="MRN Conflict Label",
        compute="_compute_duplicate_partners",
    )

    # ── same_name_partner_id is computed separately ──

    @api.depends("name")
    def _compute_same_name_partner_id(self):
        for partner in self:
            partner.same_name_partner_id = False
            if not partner.name:
                continue
            duplicate = self.env["res.partner"].with_context(active_test=False).sudo().search([
                ("name", "=", partner.name),
                ("id", "!=", partner.id),
            ], limit=1)
            partner.same_name_partner_id = duplicate if duplicate else False

    # ── phone/mobile + MRN duplicates ──────────

    @api.depends("phone", "mobile", "mrn")
    def _compute_duplicate_partners(self):
        for partner in self:
            partner.same_contact_partner_id = False
            partner.contact_conflict_label = False
            partner.same_mrn_partner_id = False
            partner.mrn_conflict_label = False

            if not partner._origin.id:
                continue

            # Duplicate Phone / Mobile
            contact_values = set(filter(None, [partner.phone, partner.mobile]))
            duplicate_contact = False
            if contact_values:
                duplicate_contact = self.env["res.partner"].with_context(active_test=False).sudo().search(
                    [
                        ("id", "!=", partner.id),
                        "|",
                        ("mobile", "in", list(contact_values)),
                        ("phone", "in", list(contact_values)),
                    ],
                    limit=1,
                )
            partner.same_contact_partner_id = duplicate_contact
            partner.contact_conflict_label = "Phone/Mobile" if duplicate_contact else False

            # Duplicate MRN
            if partner.mrn:
                duplicate_mrn = self.env["res.partner"].search(
                    [
                        ("id", "!=", partner.id),
                        ("mrn", "=", partner.mrn),
                    ],
                    limit=1,
                )
                partner.same_mrn_partner_id = duplicate_mrn
                partner.mrn_conflict_label = "MRN" if duplicate_mrn else False

    # ── chatter logging  ────────────────────────

    def _log_duplicate_info_to_chatter_once(self):
        logged_ids = set()

        for partner in self:
            if partner.id in logged_ids:
                continue
            logged_ids.add(partner.id)

            messages = []

            # Duplicate name
            if partner.name:
                duplicate_name = self.env['res.partner'].sudo().search([
                    ('name', '=', partner.name),
                    ('id', '!=', partner.id),
                ], limit=1)
                if duplicate_name:
                    messages.append(_("Duplicate contact name created"))

            # Duplicate phone/mobile
            contact_values = set(filter(None, [partner.phone, partner.mobile]))
            if contact_values:
                duplicate_contact = self.env['res.partner'].sudo().search([
                    ('id', '!=', partner.id),
                    '|',
                    ('mobile', 'in', list(contact_values)),
                    ('phone', 'in', list(contact_values)),
                ], limit=1)
                if duplicate_contact:
                    messages.append(_("Duplicate contact mobile created"))

            # Duplicate MRN
            if partner.mrn:
                duplicate_mrn = self.env['res.partner'].sudo().search([
                    ('mrn', '=', partner.mrn),
                    ('id', '!=', partner.id),
                ], limit=1)
                if duplicate_mrn:
                    messages.append(_("Duplicate MRN created"))

            for msg in messages:
                partner.message_post(
                    body=msg,
                    subject=_("Duplicate Information Detected"),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )

    # ── create  ───────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_duplicate_policy(vals)

        # Suppress chatter log during the write calls triggered inside create
        self = self.with_context(skip_duplicate_log=True)
        partners = super().create(vals_list)

        current_user = self.env.user
        current_company = self.env.company
        partners.user_id = current_user
        partners.company_id = current_company

        # Log duplicates once, after full creation
        partners._log_duplicate_info_to_chatter_once()

        return partners

    # ── write  ─────────────────

    def write(self, vals):
        for rec in self:
            self._check_duplicate_policy(vals, record=rec)

        res = super().write(vals)

        if not self.env.context.get('skip_duplicate_log'):
            self._log_duplicate_info_to_chatter_once()

        return res

    # ── block policy ─────────────────────────────────────────

    def _check_duplicate_policy(self, vals, record=None):
        policy = self.env['ir.config_parameter'].sudo().get_param(
            'ergonomiccare_implementation.duplicate_contact_policy', 'warning'
        )

        if policy != 'block':
            return

        name   = vals.get('name')   if vals.get('name')   is not None else (record.name   if record else False)
        phone  = vals.get('phone')  if vals.get('phone')  is not None else (record.phone  if record else False)
        mobile = vals.get('mobile') if vals.get('mobile') is not None else (record.mobile if record else False)
        mrn    = vals.get('mrn')    if vals.get('mrn')    is not None else (record.mrn    if record else False)

        errors = []
        rid = record.id if record else 0

        def _fmt(p):
            return p.name or 'No Name'

        if name:
            dup = self.env['res.partner'].sudo().search([('name', '=', name), ('id', '!=', rid)], limit=1)
            if dup:
                errors.append(_("Name already exists: %s") % _fmt(dup))

        if phone:
            dup = self.env['res.partner'].sudo().search([('phone', '=', phone), ('id', '!=', rid)], limit=1)
            if dup:
                errors.append(_("Phone already exists: %s → %s") % (phone, _fmt(dup)))

        if mobile:
            dup = self.env['res.partner'].sudo().search([('mobile', '=', mobile), ('id', '!=', rid)], limit=1)
            if dup:
                errors.append(_("Mobile already exists: %s → %s") % (mobile, _fmt(dup)))

        if mrn:
            dup = self.env['res.partner'].sudo().search([('mrn', '=', mrn), ('id', '!=', rid)], limit=1)
            if dup:
                errors.append(_("MRN already exists: %s → %s") % (mrn, _fmt(dup)))

        if errors:
            raise ValidationError(
                _("Duplicate detected:\n- %s") % "\n- ".join(errors)
            )

    def _format_uae_number(self, phone):
        if not phone:
            return False

        digits = re.sub(r"\D", "", phone)

        # Normalize UAE numbers
        if digits.startswith("0"):
            digits = "971" + digits[1:]
        elif digits.startswith("971"):
            pass
        else:
            return phone  # not UAE / already has + → keep original

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
            ("phone", "ilike", "05%"),
            ("mobile", "ilike", "05%"),
        ])

        for p in partners:
            vals = {}

            if p.phone:
                formatted_phone = self._format_uae_number(p.phone)
                if formatted_phone and formatted_phone != p.phone:
                    vals["phone"] = formatted_phone

            if p.mobile:
                formatted_mobile = self._format_uae_number(p.mobile)
                if formatted_mobile and formatted_mobile != p.mobile:
                    vals["mobile"] = formatted_mobile

            if vals:
                p.write(vals)

    @api.model
    def init(self):
        env = api.Environment(self._cr, SUPERUSER_ID, {})
        env["res.partner"]._run_mobile_fix()