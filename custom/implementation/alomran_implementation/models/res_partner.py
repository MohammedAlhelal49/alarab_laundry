from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
import re
from odoo.tools import html2plaintext
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    date_of_birth = fields.Date(string='Date of Birth')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender')
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ], string='Marital Status')
    nationality = fields.Many2one('res.country', string='Nationality')
    nationality_state_id = fields.Many2one(
        'res.country.state',
        string='City',
        domain="[('country_id', '=?', nationality)]"
    )
    school_university = fields.Char(string='School / University')
    major_degree = fields.Char(string='Major / Degree')
    curriculum = fields.Char(string='Curriculum')

    # Holds a reference to another partner with the same phone or mobile number (if exists)
    same_contact_partner_id = fields.Many2one(
        'res.partner',
        string='Partner with Same Phone/Mobile',
        compute='_compute_same_contact_partner_id',
        store=False
    )

    # Label used in the phone/mobile conflict warning
    contact_conflict_label = fields.Char(
        string='Conflict Label',
        compute='_compute_contact_conflict_label',
        store=False
    )

    # Holds a reference to another partner with the same name (if exists)
    same_name_partner_id = fields.Many2one(
        'res.partner',
        string='Partner with Same Name',
        compute='_compute_same_name_partner_id',
        store=True
    )
    contract_date = fields.Datetime(
        string='Contract Date',
        copy=False,
        default=lambda self: fields.Datetime.now(),
    )


    def _customer_filter_user_scope(self):
        """Return the scope the current user falls into for the
        customer-context partner filter:

          * 'bypass'    → no filter (Access Rights Administrator)
          * 'all_docs'  → hide independent individuals
          * 'own_docs'  → only own partners
          * 'none'      → no sales permission; no extra filter
        """
        user = self.env.user
        if user.has_group('base.group_erp_manager'):
            return 'bypass'
        if user.has_group('sales_team.group_sale_salesman_all_leads'):
            # includes Sales Manager via group inheritance
            return 'all_docs'
        if user.has_group('sales_team.group_sale_salesman'):
            return 'own_docs'
        return 'none'

    @api.model
    def _apply_customer_dropdown_filter(self, domain):
        """Scope partner lookups triggered from a 'customer' context
        (CRM dropdowns, Sales Customers page, etc.) based on the
        current user's permission level.
        """
        if self.env.context.get('res_partner_search_mode') != 'customer':
            return domain

        scope = self._customer_filter_user_scope()

        if scope == 'bypass' or scope == 'none':
            return domain

        if scope == 'all_docs':
            # Hide independent individuals (no parent, not a company)
            extra = [
                ('company_id', '!=', False)]

        else:  # own_docs
            extra = [('user_id', '=', self.env.uid)]

        return list(domain) + extra if domain else extra



    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0,
                        limit=None, order=None, count_limit=None):
        """Scope the initial dropdown/list shown before typing."""
        domain = self._apply_customer_dropdown_filter(domain)
        return super().web_search_read(
            domain=domain, specification=specification, offset=offset,
            limit=limit, order=order, count_limit=count_limit,
        )

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Scope typed-in searches for consistency with web_search_read."""
        args = self._apply_customer_dropdown_filter(args)
        return super().name_search(
            name=name, args=args, operator=operator, limit=limit,
        )

    def handle_users_product_creation_group(self):
        product_group = self.env.ref('product.group_product_manager')
        account_manager_group = self.env.ref('account.group_account_manager')

        # Find all users who have the product group
        users_with_product_group = self.env['res.users'].search([('groups_id', 'in', product_group.id)])

        for user in users_with_product_group:
            # If user does not have the accounting manager group → remove product group
            if account_manager_group not in user.groups_id:
                user.write({'groups_id': [(3, product_group.id)]})

    def restrict_contacts_menu_visibility_records(self):
        support_group = self.env.ref('dekad_super_user.group_de_support')
        account_manager_group = self.env.ref('account.group_account_manager')
        try:
            # sale_customers_menu_record = self.env.ref('sale.res_partner_menu')
            # if sale_customers_menu_record:
            #     sale_customers_menu = self.env['ir.ui.menu'].browse(sale_customers_menu_record.id)
            #     sale_customers_menu.write({
            #         'groups_id': [(6, 0, [support_group.id])], 'name': 'All Customers'
            #     })
            #     sale_customers_menu.unlink()
            contacts_menu_record = self.env.ref('contacts.menu_contacts')
            if contacts_menu_record:
                contacts_menu = self.env['ir.ui.menu'].browse(contacts_menu_record.id)
                contacts_menu.write({
                    'groups_id': [(6, 0, [account_manager_group.id])]
                })
        except ValueError:
            _logger.warning("Contacts Module dosent exist")

    # Computes and sets the partner with the same phone or mobile (if any)
    @api.depends('mobile', 'phone')
    def _compute_same_contact_partner_id(self):
        for partner in self:
            partner_id = partner._origin.id
            partner.same_contact_partner_id = False

            contact_values = set(filter(None, [partner.phone, partner.mobile]))

            if not contact_values:
                continue

            domain = [
                ('id', '!=', partner_id),
                '|',
                ('mobile', 'in', list(contact_values)),
                ('phone', 'in', list(contact_values))
            ]

            duplicate = self.env['res.partner'].with_context(active_test=False).sudo().search(domain, limit=1)

            partner.same_contact_partner_id = duplicate if duplicate else False

    @api.depends('mobile', 'phone')
    def _compute_contact_conflict_label(self):
        for partner in self:
            partner.contact_conflict_label = _("Phone/Mobile")

    # Computes and sets the partner with the same name (if any)
    @api.depends('name')
    def _compute_same_name_partner_id(self):
        for partner in self:
            partner.same_name_partner_id = False
            if not partner.name:
                continue
            duplicate = self.env['res.partner'].with_context(active_test=False).sudo().search([
                ('name', '=', partner.name),
                ('id', '!=', partner.id)
            ], limit=1)
            partner.same_name_partner_id = duplicate if duplicate else False

    @api.model_create_multi
    def create(self, vals_list):
        #  CHECK BEFORE CREATE
        for vals in vals_list:
            self._check_duplicate_policy(vals)

        # Temporarily disable chatter log in write triggered during create
        self = self.with_context(skip_duplicate_log=True)
        partners = super().create(vals_list)

        current_user = self.env.user
        current_company = self.env.company
        partners.user_id = current_user
        partners.company_id = current_company

        # Log duplicates once after full creation
        partners._log_duplicate_info_to_chatter_once()

        return partners

    def write(self, vals):
        #  CHECK BEFORE WRITE
        for rec in self:
            self._check_duplicate_policy(vals, record=rec)

        res = super().write(vals)

        if not self.env.context.get('skip_duplicate_log'):
            self._log_duplicate_info_to_chatter_once()

        return res

    def _log_duplicate_info_to_chatter_once(self):
        logged_ids = set()

        for partner in self:
            if partner.id in logged_ids:
                continue
            logged_ids.add(partner.id)

            messages = []

            # Check for duplicate name
            if partner.name:
                duplicate_name = self.env['res.partner'].sudo().search([
                    ('name', '=', partner.name),
                    ('id', '!=', partner.id)
                ], limit=1)
                if duplicate_name:
                    messages.append("Duplicate contact name created")

            # Check for duplicate phone/mobile
            contact_values = set(filter(None, [partner.phone, partner.mobile]))
            if contact_values:
                duplicate_contact = self.env['res.partner'].sudo().search([
                    ('id', '!=', partner.id),
                    '|',
                    ('mobile', 'in', list(contact_values)),
                    ('phone', 'in', list(contact_values))
                ], limit=1)
                if duplicate_contact:
                    messages.append("Duplicate contact mobile created")

            for msg in messages:
                partner.message_post(
                    body=msg,
                    subject="Duplicate Information Detected",
                    message_type='comment',
                    subtype_xmlid='mail.mt_note'
                )

    @api.depends_context('show_address', 'partner_show_db_id', 'address_inline', 'show_email', 'lang')
    def _compute_display_name(self):
        for partner in self:
            name = partner.with_context(lang=self.env.lang)._get_complete_name()

            #  Use mobile and/or phone if show_address is set
            if partner._context.get('show_address'):
                contact_parts = []
                if partner.mobile:
                    contact_parts.append(partner.mobile)
                if partner.phone and partner.phone != partner.mobile:
                    contact_parts.append(partner.phone)
                if contact_parts:
                    name = f"{name}\n{' / '.join(contact_parts)}"

            name = re.sub(r'\s+\n', '\n', name)

            if partner._context.get('partner_show_db_id'):
                name = f"{name} ({partner.id})"
            if partner._context.get('address_inline'):
                name = ", ".join([n.strip() for n in name.split("\n") if n.strip()])
            if partner._context.get('show_email') and partner.email:
                name = f"{name} <{partner.email}>"
            # No show_vat logic
            partner.display_name = name.strip()

    @api.constrains('comment')
    def _check_internal_notes_min_length(self):
        for rec in self:
            if rec.comment:
                plain_text = html2plaintext(rec.comment).strip()
                if len(plain_text) < 50:
                    raise ValidationError(
                        _("Internal Notes must be at least 50 characters.")
                    )

    @api.onchange('nationality')
    def _onchange_nationality(self):
        for rec in self:
            if rec.nationality and rec.nationality != rec.nationality_state_id.country_id:
                rec.nationality_state_id = False

    def _format_uae_number(self, phone):

        if not phone:
            return False

        digits = re.sub(r"\D", "", phone)

        # Normalize UAE numbers

        if digits.startswith("00971"):

            digits = digits[2:]

        elif digits.startswith("971"):

            pass

        elif digits.startswith("0"):

            digits = "971" + digits[1:]

        elif digits.startswith("5") and len(digits) == 9:

            digits = "971" + digits

        else:

            return phone  # not UAE → keep original

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


    def _check_duplicate_policy(self, vals, record=None):
        if self.env.context.get('skip_duplicate_check'):
            return

        policy = self.env.company.duplicate_contact_policy

        if policy != "block":
            return

        name = (
            vals.get("name")
            if "name" in vals
            else (record.name if record else False)
        )
        phone = (
            vals.get("phone")
            if "phone" in vals
            else (record.phone if record else False)
        )
        mobile = (
            vals.get("mobile")
            if "mobile" in vals
            else (record.mobile if record else False)
        )

        errors = []

        def _partner_info(partner):
            company = partner.company_id.name if partner.company_id else _("No Company")
            return f"{partner.name} ({company})"

        # ----------------------------------------------------
        # Duplicate Name
        # ----------------------------------------------------
        if name:
            duplicate_name = self.env["res.partner"].sudo().search([
                ("name", "=", name),
                ("id", "!=", record.id if record else 0),
            ], limit=1)

            if duplicate_name:
                errors.append(
                    _("Name already exists: %s") % _partner_info(duplicate_name)
                )

        # ----------------------------------------------------
        # Duplicate Phone / Mobile
        # (phone↔phone, phone↔mobile, mobile↔phone, mobile↔mobile)
        # ----------------------------------------------------
        contact_values = list(filter(None, [phone, mobile]))

        if contact_values:
            duplicate_contact = self.env["res.partner"].sudo().search([
                ("id", "!=", record.id if record else 0),
                "|",
                ("phone", "in", contact_values),
                ("mobile", "in", contact_values),
            ], limit=1)

            if duplicate_contact:
                duplicate_number = (
                    duplicate_contact.phone
                    if duplicate_contact.phone in contact_values
                    else duplicate_contact.mobile
                )

                errors.append(
                    _("Phone/Mobile already exists: %s → %s") % (
                        duplicate_number,
                        _partner_info(duplicate_contact),
                    )
                )

        # ----------------------------------------------------
        # Block
        # ----------------------------------------------------
        if errors:
            raise ValidationError(
                _("Duplicate contact detected:\n- %s") % "\n- ".join(errors)
            )

    @api.model
    def _run_full_mobile_fix(self):

        fixed = {'res.partner': 0, 'crm.lead': 0}

        for model_name in ('res.partner', 'crm.lead'):
            Model = self.env[model_name].sudo().with_context(active_test=False)
            records = Model.search([
                '|',
                ('phone', '!=', False),
                ('mobile', '!=', False),
            ])

            for rec in records:
                vals = {}

                if rec.phone:
                    formatted_phone = self._format_uae_number(rec.phone)
                    if formatted_phone and formatted_phone != rec.phone:
                        vals['phone'] = formatted_phone

                if rec.mobile:
                    formatted_mobile = self._format_uae_number(rec.mobile)
                    if formatted_mobile and formatted_mobile != rec.mobile:
                        vals['mobile'] = formatted_mobile

                if vals:
                    rec.write(vals)
                    fixed[model_name] += 1

        return fixed

    has_duplicate = fields.Boolean(
        compute="_compute_has_duplicate",
        store=True,
        index=True,
    )

    @api.depends("name", "phone", "mobile")
    def _compute_has_duplicate(self):
        Partner = self.env["res.partner"].sudo()

        for partner in self:
            partner.has_duplicate = False

            # Duplicate name
            if partner.name:
                duplicate = Partner.search([
                    ("name", "=", partner.name),
                    ("id", "!=", partner.id),
                ], limit=1)

                if duplicate:
                    partner.has_duplicate = True
                    continue

            # Duplicate phone/mobile
            contact_values = list(set(filter(None, [partner.phone, partner.mobile])))
            if not contact_values:
                continue

            duplicate = Partner.search([
                ("id", "!=", partner.id),
                "|",
                ("phone", "in", contact_values),
                ("mobile", "in", contact_values),
            ], limit=1)

            partner.has_duplicate = bool(duplicate)


    has_contact_duplicate = fields.Boolean(
        string="Has Contact Duplicate",
        compute="_compute_has_contact_duplicate",
        store=True,
        index=True,
    )

    @api.depends("phone", "mobile")
    def _compute_has_contact_duplicate(self):
        Partner = self.env["res.partner"].sudo()

        for partner in self:
            partner.has_contact_duplicate = False

            contact_values = list(set(filter(None, [partner.phone, partner.mobile])))
            if not contact_values:
                continue

            duplicate = Partner.search([
                ("id", "!=", partner.id),
                "|",
                ("phone", "in", contact_values),
                ("mobile", "in", contact_values),
            ], limit=1)

            partner.has_contact_duplicate = bool(duplicate)

    def _get_partner_activity_date(self, partner):
        """Last relevant activity date for a single partner: chatter on
        its own linked non-won opportunities, or (if it has none) its
        own chatter + write_date."""
        leads = self.env['crm.lead'].sudo().search([
            ('partner_id', '=', partner.id),
            ('stage_id.is_won', '=', False),
        ])

        if leads:
            last_message = self.env['mail.message'].sudo().search([
                ('model', '=', 'crm.lead'),
                ('res_id', 'in', leads.ids),
                ('message_type', 'in', ['comment', 'notification']),
            ], order='date desc', limit=1)
            return last_message.date if last_message else max(leads.mapped('create_date'))

        candidate_dates = [
            d for d in (partner.last_chatter_activity_date, partner.write_date) if d
        ]
        return max(candidate_dates) if candidate_dates else None

    def _get_all_duplicate_contact_partners(self, partner):
        """All OTHER partners sharing partner's phone/mobile."""
        contact_values = list(set(filter(None, [partner.phone, partner.mobile])))
        if not contact_values:
            return self.env['res.partner']
        return self.env['res.partner'].with_context(active_test=False).sudo().search([
            ('id', '!=', partner.id),
            '|',
            ('phone', 'in', contact_values),
            ('mobile', 'in', contact_values),
        ])

    def _get_all_duplicate_name_partners(self, partner):
        """All OTHER partners sharing partner's exact name."""
        if not partner.name:
            return self.env['res.partner']
        return self.env['res.partner'].with_context(active_test=False).sudo().search([
            ('id', '!=', partner.id),
            ('name', '=', partner.name),
        ])

    def _is_duplicate_inactive_via_crm_leads(self, duplicate_partner, all_duplicates=None):
        """Eligible for takeover only if EVERY matching duplicate partner
        (not just the first one found) is inactive for 30+ days, per
        _get_partner_activity_date."""
        if not duplicate_partner:
            return False

        partners_to_check = all_duplicates if all_duplicates is not None else duplicate_partner
        if not partners_to_check:
            return False

        cutoff = fields.Datetime.now() - timedelta(days=30)

        for partner in partners_to_check:
            last_activity = self._get_partner_activity_date(partner)
            if not last_activity or last_activity >= cutoff:
                return False  # at least one duplicate is still active

        return True

    last_chatter_activity_date = fields.Datetime(
        string='Last Chatter Activity',
        compute='_compute_last_chatter_activity_date',
        store=True,
    )

    @api.depends('message_ids.date')
    def _compute_last_chatter_activity_date(self):
        for partner in self:
            last_message = self.env['mail.message'].sudo().search([
                ('model', '=', 'res.partner'),
                ('res_id', '=', partner.id),
                ('message_type', 'in', ['comment', 'notification']),
            ], order='date desc', limit=1)
            partner.last_chatter_activity_date = last_message.date if last_message else partner.create_date


    same_contact_partner_inactive = fields.Boolean(
        string='Duplicate Phone/Mobile Contact Inactive 30+ Days',
        compute='_compute_same_contact_partner_inactive',
        store=False,
    )

    @api.depends('same_contact_partner_id')
    def _compute_same_contact_partner_inactive(self):
        for partner in self:
            if not partner.same_contact_partner_id:
                partner.same_contact_partner_inactive = False
                continue
            duplicates = self._get_all_duplicate_contact_partners(partner)
            partner.same_contact_partner_inactive = self._is_duplicate_inactive_via_crm_leads(
                partner.same_contact_partner_id, duplicates
            )



    same_name_partner_inactive = fields.Boolean(
        string='Duplicate Name Contact Inactive 30+ Days',
        compute='_compute_same_name_partner_inactive',
        store=False,
    )

    @api.depends('same_name_partner_id')
    def _compute_same_name_partner_inactive(self):
        for partner in self:
            if not partner.same_name_partner_id:
                partner.same_name_partner_inactive = False
                continue
            duplicates = self._get_all_duplicate_name_partners(partner)
            partner.same_name_partner_inactive = self._is_duplicate_inactive_via_crm_leads(
                partner.same_name_partner_id, duplicates
            )


    @api.model
    def action_takeover_duplicate_partner(self, duplicate_id):
        duplicate = self.browse(duplicate_id).exists()

        if not duplicate:
            raise ValidationError(_("The existing contact could not be found."))

        # Collect all phone/mobile values from the selected duplicate
        contact_values = list(set(filter(None, [
            duplicate.phone,
            duplicate.mobile,
        ])))

        if not contact_values:
            return True

        # Find ALL partners having the same phone/mobile
        duplicates = self.env["res.partner"].with_context(
            active_test=False
        ).sudo().search([
            "|",
            ("phone", "in", contact_values),
            ("mobile", "in", contact_values),
        ])

        duplicates.with_context(skip_duplicate_check=True).write({
            "user_id": self.env.user.id,
            "company_id": self.env.company.id,
        })

        for partner in duplicates:
            partner.message_post(
                body=_(
                    "Reassigned to %s (%s) after taking over an inactive duplicate contact."
                ) % (
                         self.env.user.name,
                         self.env.company.name,
                     ),
                subject=_("Contact Reassigned"),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

        # Also reassign any linked opportunities (crm.lead) to the
        # current user/company, so the salesperson owns the pipeline
        # too, not just the contact card.
        leads = self.env["crm.lead"].sudo().search([
            ("partner_id", "in", duplicates.ids),
            ("stage_id.is_won", "=", False),
        ])

        if leads:
            leads.write({
                "user_id": self.env.user.id,
                "company_id": self.env.company.id,
            })

            for lead in leads:
                lead.message_post(
                    body=_(
                        "Reassigned to %s (%s) after taking over an inactive duplicate contact."
                    ) % (
                             self.env.user.name,
                             self.env.company.name,
                         ),
                    subject=_("Opportunity Reassigned"),
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                )

        return True


class ResUsers(models.Model):
    _inherit = 'res.users'


    def assign_customers_domain(self):
        """
        Assign 'Partner: Own Contacts Only' group automatically
        to sales users who have:
            - Sales: Own Documents Only
            - NOT Sales: All Documents
        """

        group_own_sale = self.env.ref(
            'sales_team.group_sale_salesman'
        )
        group_all_sale = self.env.ref(
            'sales_team.group_sale_salesman_all_leads'
        )
        group_partner_limit = self.env.ref(
            'dekad_partner_access_fix.group_partner_own_contacts_only'
        )

        users = self.search([
            ('groups_id', 'in', group_own_sale.id),
            ('groups_id', 'not in', group_all_sale.id),
        ])
        print(users)
        # Only users missing the restriction group
        users_to_update = users.filtered(
            lambda u: group_partner_limit not in u.groups_id
        )
        print(users_to_update)

        if users_to_update:
            users_to_update.write({
                'groups_id': [(4, group_partner_limit.id)]
            })

        return {
            'total_sales_users': len(users),
            'updated_users': len(users_to_update),
        }

