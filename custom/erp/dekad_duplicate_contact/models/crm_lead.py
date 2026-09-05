from odoo import models, fields, api, _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Kept in sync with the linked contact's mobile
    mobile = fields.Char(
        string='Mobile',
        compute='_compute_mobile',
        inverse='_inverse_mobile',
        readonly=False,
        store=True,
    )

    same_contact_partner_id = fields.Many2one(
        'res.partner',
        string='Duplicate Phone/Mobile',
        compute='_compute_duplicate_contact_partner',
    )

    contact_conflict_label = fields.Char(
        compute='_compute_duplicate_contact_partner',
    )

    @api.depends('partner_id.mobile')
    def _compute_mobile(self):
        for lead in self:
            if lead.partner_id:
                lead.mobile = lead.partner_id.mobile
            else:
                lead.mobile = lead.mobile

    def _inverse_mobile(self):
        for lead in self:
            if lead.partner_id and lead.partner_id.mobile != lead.mobile:
                lead.partner_id.mobile = lead.mobile

    @api.depends('partner_id.phone', 'partner_id.mobile')
    def _compute_duplicate_contact_partner(self):
        Partner = self.env['res.partner'].sudo()
        for lead in self:
            lead.same_contact_partner_id = False
            lead.contact_conflict_label = _("Phone/Mobile")

            if not lead.partner_id:
                continue

            numbers = list(filter(None, [lead.partner_id.phone, lead.partner_id.mobile]))
            if not numbers:
                continue

            duplicate = Partner.with_context(active_test=False).search([
                ('id', '!=', lead.partner_id.id),
                '|',
                ('phone', 'in', numbers),
                ('mobile', 'in', numbers),
            ], limit=1)
            lead.same_contact_partner_id = duplicate
