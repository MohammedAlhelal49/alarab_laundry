# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CrmReservation(models.Model):
    _name = 'crm.reservation'
    _description = 'CRM Reservation'
    _order = 'reservation_datetime desc, id desc'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reservation Number', required=True, copy=False,
        readonly=True, default=lambda self: _('New'))
    patient_id = fields.Many2one(
        'res.partner', string='Patient', required=True, ondelete='restrict',
        tracking=True)
    lead_id = fields.Many2one(
        'crm.lead',
        string='Lead',
        ondelete='set null',
        index=True,
        tracking=True,
    )

    phone = fields.Char(
        string='Phone',
        related='patient_id.phone',
        store=True,
        readonly=True,
    )

    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        default=lambda self: self.env.user,
        tracking=True,
    )
    mobile = fields.Char(
        string='Mobile Number',
        related='patient_id.mobile',
        store=True,
        readonly=True,
    )
    function = fields.Char(
        string='File Number',
        related='patient_id.function',
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    doctor_id = fields.Many2one('hr.employee', string='Doctor',domain="[('employee_group_id.code', '=', 'doctor')]", tracking=True)
    reservation_datetime = fields.Datetime(
        string='Reservation Date & Time', required=True,
        default=fields.Datetime.now, tracking=True)
    reception_note = fields.Text(string='Reception Note')
    saleman_note = fields.Text(string='Sales Man Note')

    doctor_note = fields.Text(string='Doctor Note')
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('arrived', 'Arrived'),
        ('delayed', 'Delayed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled', required=True, copy=False, tracking=True)
    cancel_reason_id = fields.Many2one(
        'crm.reservation.delay.reason',
        string='Cancellation Reason',
        ondelete='restrict',
        tracking=True,
    )

    lang = fields.Selection(
        related='patient_id.lang',
        string='Language',
        store=True,
        readonly=True,
    )

    location = fields.Char(
        string='Location',
        compute='_compute_location',
        store=True,
        readonly=True,
    )

    is_arrived = fields.Boolean(
        string='Arrived',
        tracking=True,
    )

    arrival_datetime = fields.Datetime(
        string='Arrival Date & Time',
        tracking=True,
    )

    is_delayed = fields.Boolean(
        string='Delayed',
        tracking=True,
    )

    delay_reason_id = fields.Many2one(
        'crm.reservation.delay.reason',
        string='Delay Reason',
        ondelete='restrict',
        tracking=True,
    )

    related_reservation_count = fields.Integer(
        string='Related Reservations',
        compute='_compute_related_reservation_count',
    )

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)',
         'The reservation number must be unique per company!'),
    ]

    @api.depends('patient_id')
    def _compute_related_reservation_count(self):
        for rec in self:
            if not rec.patient_id:
                rec.related_reservation_count = 0
                continue

            domain = [
                ('patient_id', '=', rec.patient_id.id),
            ]

            # Don't count the reservation currently open
            if rec.id:
                domain.append(('id', '!=', rec.id))

            rec.related_reservation_count = self.search_count(domain)

    def action_view_related_reservations(self):
        self.ensure_one()

        if not self.patient_id:
            return False

        domain = [
            ('patient_id', '=', self.patient_id.id),
            ('id', '!=', self.id),
        ]

        return {
            'name': _('Related Reservations - %s') % self.patient_id.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'crm.reservation',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_company_id': self.company_id.id,
            },
        }


    @api.depends(
        'patient_id',
        'patient_id.street',
        'patient_id.street2',
        'patient_id.city',
        'patient_id.state_id',
        'patient_id.country_id',
    )
    def _compute_location(self):
        for rec in self:
            partner = rec.patient_id

            if not partner:
                rec.location = False
                continue

            # Street - Street 2
            street_parts = [
                value for value in [
                    partner.street,
                    partner.street2,
                ] if value
            ]
            street = ' - '.join(street_parts)

            # City - State
            city_state_parts = [
                value for value in [
                    partner.city,
                    partner.state_id.name,
                ] if value
            ]
            city_state = ' - '.join(city_state_parts)

            # Street - Street 2, City - State, Country
            location_parts = [
                value for value in [
                    street,
                    city_state,
                    partner.country_id.name,
                ] if value
            ]

            rec.location = ', '.join(location_parts)

    @api.onchange('lead_id')
    def _onchange_lead_id(self):
        if self.lead_id:
            self.patient_id = self.lead_id.partner_id
            self.salesperson_id = self.lead_id.user_id

    @api.constrains('state', 'cancel_reason_id')
    def _check_cancel_reason(self):
        for rec in self:
            if rec.state == 'cancelled' and not rec.cancel_reason_id:
                raise ValidationError(_(
                    'Please select a cancellation reason before cancelling reservation %s.'
                ) % (rec.name or '')
                                      )


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                company_id = vals.get('company_id') or self.env.company.id
                vals['name'] = self.env['ir.sequence'].with_company(company_id).next_by_code(
                    'crm.reservation') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        if 'name' in vals:
            for rec in self:
                if rec.name and rec.name != _('New') and vals.get('name') != rec.name:
                    raise ValidationError(_('The reservation number cannot be changed manually.'))
        return super().write(vals)

    def action_cancel(self):
        self.ensure_one()
        return {
            'name': _('Cancel Reservation'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.reservation.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_reservation_id': self.id},
        }

    @api.onchange('is_arrived')
    def _onchange_is_arrived(self):
        if self.is_arrived:
            self.state = 'arrived'
        elif self.state == 'arrived':
            if self.is_delayed:
                self.state = 'delayed'
            else:
                self.state = 'scheduled'
            self.arrival_datetime = False

    @api.onchange('is_delayed')
    def _onchange_is_delayed(self):
        if self.is_delayed:
            # If already arrived, Arrived remains the final/current status.
            if not self.is_arrived:
                self.state = 'delayed'
        else:
            self.delay_reason_id = False

            if self.is_arrived:
                self.state = 'arrived'
            elif self.state == 'delayed':
                self.state = 'scheduled'


    @api.constrains(
        'is_arrived',
        'is_delayed',
        'arrival_datetime',
        'delay_reason_id',
    )
    def _check_arrival_delay(self):
        for rec in self:

            if rec.is_arrived and not rec.arrival_datetime:
                raise ValidationError(_(
                    'Please enter the arrival date and time.'
                ))

            if rec.is_delayed and not rec.delay_reason_id:
                raise ValidationError(_(
                    'Please select a delay reason.'
                ))

class CrmReservationCancelWizard(models.TransientModel):
    _name = 'crm.reservation.cancel.wizard'
    _description = 'Cancel Reservation Wizard'

    reservation_id = fields.Many2one(
        'crm.reservation', string='Reservation', required=True)
    cancel_reason_id = fields.Many2one(
        'crm.reservation.delay.reason',
        string='Cancellation Reason',
        required=True,
        ondelete='restrict',
    )
    def action_confirm_cancel(self):
        self.ensure_one()
        self.reservation_id.write({
            'state': 'cancelled',
            'cancel_reason_id': self.cancel_reason_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}


class CrmReservationDelayReason(models.Model):
    _name = 'crm.reservation.delay.reason'
    _description = 'Reservation Reason'
    _order = 'sequence, name'

    name = fields.Char(
        string='Reason',
        required=True,
        translate=True,
    )

    sequence = fields.Integer(
        default=10,
    )

    active = fields.Boolean(
        default=True,
    )

    _sql_constraints = [
        (
            'delay_reason_name_uniq',
            'unique(name)',
            'The delay reason must be unique!'
        ),
    ]
