from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import random
from odoo.tools import html2plaintext


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    is_tracked = fields.Boolean('Is tracked')

    date = fields.Date('Date')

    referred_by_id = fields.Many2one(
        'res.partner',
        string='Referred By',
        domain="[('customer_rank', '>', 0), ('user_id', '!=', False)]",
        help='Customer who referred this lead (must be a customer assigned to a salesperson).'
    )

    show_referred_field = fields.Boolean(
        string="Show Referred By",
        compute="_compute_show_referred_field",
        store=False
    )


    mobile = fields.Char(
        string="Mobile",
        compute="_compute_mobile",
        inverse="_inverse_mobile",
        readonly=False,
        store=True,
    )

    same_contact_partner_id = fields.Many2one(
        "res.partner",
        compute="_compute_duplicate_partners",
        string="Duplicate Phone/Mobile",
    )

    same_name_partner_id = fields.Many2one(
        "res.partner",
        compute="_compute_duplicate_partners",
        string="Duplicate Name",
    )

    contact_conflict_label = fields.Char(
        compute="_compute_duplicate_partners",
    )

    @api.depends("partner_id.mobile")
    def _compute_mobile(self):
        super()._compute_mobile()

    def _inverse_mobile(self):
        for lead in self:
            if lead.partner_id and lead.partner_id.mobile != lead.mobile:
                lead.partner_id.mobile = lead.mobile

    @api.depends("partner_id", "partner_id.name", "partner_id.phone", "partner_id.mobile")
    def _compute_duplicate_partners(self):
        Partner = self.env["res.partner"].sudo()

        for lead in self:
            lead.same_contact_partner_id = False
            lead.same_name_partner_id = False
            lead.contact_conflict_label = _("Phone/Mobile")

            if not lead.partner_id:
                continue

            # Duplicate name
            if lead.partner_id.name:
                duplicate_name = Partner.search([
                    ("name", "=", lead.partner_id.name),
                    ("id", "!=", lead.partner_id.id),
                ], limit=1)
                lead.same_name_partner_id = duplicate_name

            # Duplicate phone/mobile
            numbers = list(filter(None, [
                lead.partner_id.phone,
                lead.partner_id.mobile,
            ]))

            if numbers:
                duplicate_contact = Partner.search([
                    ("id", "!=", lead.partner_id.id),
                    "|",
                    ("phone", "in", numbers),
                    ("mobile", "in", numbers),
                ], limit=1)

                lead.same_contact_partner_id = duplicate_contact



    @api.depends('source_id')
    def _compute_show_referred_field(self):
        for lead in self:
            lead.show_referred_field = lead.source_id and lead.source_id.name == 'Referral'

    @api.constrains('description')
    def _check_internal_notes_min_length(self):
        for rec in self:
            if rec.description:
                plain_text = html2plaintext(rec.description).strip()
                if len(plain_text) < 50:
                    raise ValidationError(
                        _("Internal Notes must be at least 50 characters.")
                    )

    # Prevent duplicate opportunities with the same customer and title.
    @api.constrains('partner_id', 'name')
    def _check_duplicate_opportunity(self):
        for lead in self:
            if lead.type != 'opportunity' or not lead.partner_id or not lead.name:
                continue

            domain = [
                ('id', '!=', lead.id),
                ('type', '=', 'opportunity'),
                ('partner_id', '=', lead.partner_id.id),
                ('name', '=', lead.name),
            ]
            duplicate = self.search(domain, limit=1)
            if duplicate:
                raise ValidationError(_(
                    "A duplicate opportunity already exists for the same customer with the same title: %s" % lead.name
                ))

    @api.model
    def cron_auto_transfer_inactive_opportunities(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        enabled = ICPSudo.get_param('alomran_implementation.enable_auto_transfer') == 'True'
        duration_days = int(ICPSudo.get_param('alomran_implementation.auto_transfer_duration_days', default=10))

        if not enabled or duration_days <= 0:
            return

        # Calculate the cutoff date
        cutoff_date = fields.Datetime.now() - timedelta(days=duration_days)

        # Search for opportunities in "New" stage (assumption: name='New') and inactive
        leads = self.search([
            ('type', '=', 'opportunity'),
            ('stage_id.name', '=', 'New'),
            ('write_date', '<=', cutoff_date),
            ('user_id', '!=', False),
            ('active', '=', True)
        ])

        all_users = self.env['res.users'].search([('share', '=', False), ('active', '=', True)])

        for lead in leads:
            all_users = self.env['res.users'].search([
                ('share', '=', False),
                ('active', '=', True),
                '|',
                ('company_id', '=', lead.company_id.id),
                ('company_ids', 'in', lead.company_id.id)
            ])

            possible_users = all_users.filtered(lambda u: u.id != lead.user_id.id)
            if not possible_users:
                continue

            new_user = random.choice(possible_users)
            old_user = lead.user_id

            lead.sudo().with_context(force_company=lead.company_id.id).write({'user_id': new_user.id})

            lead.message_post(body=_(
                "Salesperson automatically changed from %s to %s due to inactivity."
            ) % (old_user.name, new_user.name))



    same_contact_partner_inactive = fields.Boolean(
        string='Duplicate Phone/Mobile Contact Inactive 30+ Days',
        compute='_compute_partner_duplicate_inactive',
    )

    @api.depends('same_contact_partner_id', 'partner_id')
    def _compute_partner_duplicate_inactive(self):
        Partner = self.env['res.partner']
        for lead in self:
            if not lead.same_contact_partner_id or not lead.partner_id:
                lead.same_contact_partner_inactive = False
                continue
            duplicates = Partner._get_all_duplicate_contact_partners(lead.partner_id)
            lead.same_contact_partner_inactive = Partner._is_duplicate_inactive_via_crm_leads(
                lead.same_contact_partner_id, duplicates
            )

    def _takeover_duplicate_partner(self, duplicate):
        self.ensure_one()
        if not duplicate:
            raise ValidationError(_("The existing contact could not be found."))

        self.env['res.partner'].action_takeover_duplicate_partner(duplicate.id)
        self.write({'partner_id': duplicate.id})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Contact Reassigned'),
                'message': _('"%s" has been reassigned to you and linked to this record.') % duplicate.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_takeover_same_contact_partner(self):
        self.ensure_one()
        return self._takeover_duplicate_partner(self.same_contact_partner_id)


class UtmSource(models.Model):
    _inherit = 'utm.source'

    _order = 'name asc'
