from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Points to another contact sharing the same phone/mobile, if any.
    same_contact_partner_id = fields.Many2one(
        'res.partner',
        string='Contact with Same Phone/Mobile',
        compute='_compute_same_contact_partner_id',
        store=False,
    )

    # Label used in the warning banner ("Phone/Mobile").
    contact_conflict_label = fields.Char(
        string='Conflict Label',
        compute='_compute_contact_conflict_label',
    )

    @api.depends('phone', 'mobile')
    def _compute_same_contact_partner_id(self):
        for partner in self:
            partner.same_contact_partner_id = partner._find_duplicate_contact_partner()

    def _compute_contact_conflict_label(self):
        for partner in self:
            partner.contact_conflict_label = _("Phone/Mobile")

    def _find_duplicate_contact_partner(self):
        """Return the first OTHER contact sharing this contact's phone or
        mobile number (archived contacts included), if any."""
        self.ensure_one()
        contact_values = list(set(filter(None, [self.phone, self.mobile])))
        if not contact_values:
            return self.env['res.partner']

        partner_id = self._origin.id
        domain = [
            ('id', '!=', partner_id or 0),
            '|',
            ('phone', 'in', contact_values),
            ('mobile', 'in', contact_values),
        ]
        return self.env['res.partner'].with_context(active_test=False).sudo().search(domain, limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_duplicate_contact_policy(vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'phone' in vals or 'mobile' in vals:
            for rec in self:
                rec._check_duplicate_contact_policy(vals, record=rec)
        return super().write(vals)

    def _check_duplicate_contact_policy(self, vals, record=None):
        """Raise if the company's policy is 'block' and the phone/mobile
        in vals (or already on `record`) matches another contact."""
        if self.env.context.get('skip_duplicate_check'):
            return

        policy = self.env.company.duplicate_contact_policy
        if policy != 'block':
            return

        phone = vals.get('phone', record.phone if record else False)
        mobile = vals.get('mobile', record.mobile if record else False)
        contact_values = list(set(filter(None, [phone, mobile])))
        if not contact_values:
            return

        domain = [
            ('id', '!=', record.id if record else 0),
            '|',
            ('phone', 'in', contact_values),
            ('mobile', 'in', contact_values),
        ]
        duplicate = self.env['res.partner'].with_context(active_test=False).sudo().search(domain, limit=1)
        if duplicate:
            duplicate_number = duplicate.phone if duplicate.phone in contact_values else duplicate.mobile
            company_name = duplicate.company_id.name if duplicate.company_id else _('No Company')
            raise ValidationError(_(
                "Duplicate contact detected.\nPhone/Mobile %(number)s already exists on: %(name)s (%(company)s)"
            ) % {
                'number': duplicate_number,
                'name': duplicate.name,
                'company': company_name,
            })
