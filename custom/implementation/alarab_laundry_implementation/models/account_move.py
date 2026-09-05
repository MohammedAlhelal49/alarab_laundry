from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    partner_contact = fields.Char(string='Contact Phone', compute='_compute_partner_contact', store=True)
    partner_address_display = fields.Char(
        string="Plate Info",
        compute='_compute_partner_address_display',
        store=True
    )

    @api.depends(
        'partner_id.street',
        'partner_id.city',
        'partner_id.zip',
        'partner_id.state_id.name',
        'partner_id.country_id.name'
    )
    def _compute_partner_address_display(self):
        for move in self:
            parts = [
                move.partner_id.street or '',
                move.partner_id.city or '',
                move.partner_id.state_id.name or '',
                move.partner_id.zip or '',
                move.partner_id.country_id.name or '',
            ]
            # Remove empty parts and join with comma
            move.partner_address_display = ', '.join(filter(None, parts))

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

    partner_contact = fields.Char(
        string='Contact Phone',
        compute='_compute_partner_contact',
        store=True,
        search='_search_partner_contact',
    )

