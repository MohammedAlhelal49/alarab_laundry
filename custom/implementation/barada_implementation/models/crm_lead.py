# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    reservation_ids = fields.One2many(
        'crm.reservation',
        'lead_id',
        string='Reservations',
    )

    reservation_count = fields.Integer(
        compute='_compute_reservation_count',
        string='Reservations Count',
    )

    def _compute_reservation_count(self):
        for lead in self:
            lead.reservation_count = self.env['crm.reservation'].search_count([
                ('lead_id', '=', lead.id)
            ])

    def _get_reservation_default_context(self):
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_(
                'Please set a Customer/Contact on this record '
                'before creating a reservation.'
            ))

        return {
            # Link reservation to this CRM lead
            'default_lead_id': self.id,

            # Patient
            'default_patient_id': self.partner_id.id,

            # Sales Man from CRM Lead
            'default_salesperson_id': self.user_id.id,

            # Company
            'default_company_id': self.company_id.id,
        }

    def action_view_reservations(self):
        self.ensure_one()

        return {
            'name': _('Reservations'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.reservation',
            'view_mode': 'list,calendar,form',
            'domain': [('lead_id', '=', self.id)],
            'context': self._get_reservation_default_context(),
        }

    def action_open_reservation_popup(self):
        """Always open a new reservation with values prefilled."""
        self.ensure_one()

        return {
            'name': _('New Reservation'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.reservation',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': self._get_reservation_default_context(),
        }