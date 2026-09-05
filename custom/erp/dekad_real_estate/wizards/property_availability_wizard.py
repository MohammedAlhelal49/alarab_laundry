from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RealEstatePropertyAvailabilityWizard(models.TransientModel):
    _name = 'real.estate.property.availability.wizard'
    _description = 'Property Availability Wizard'

    state = fields.Selection([
        ('input', 'Input'),
        ('result', 'Result'),
    ], default='input')

    building_id = fields.Many2one(
        'real.estate.buildings', string='Building', required=True,
    )
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)

    line_ids = fields.One2many(
        'real.estate.property.availability.wizard.line',
        'wizard_id', string='Properties',
    )

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for wiz in self:
            if wiz.date_start and wiz.date_end and wiz.date_start > wiz.date_end:
                raise ValidationError('Start date must be before end date.')

    def action_search(self):
        self.ensure_one()
        properties = self.env['account.analytic.account'].search([
            ('is_property', '=', True),
            ('offer_type', '=', 'rent'),
            ('property_building_id', '=', self.building_id.id),
        ])

        lines_vals = []
        for prop in properties:
            contract = self.env['sale.order'].search([
                ('account_analytic_account_id', '=', prop.id),
                ('state', '=', 'sale'),
                ('is_closed', '=', False),
                ('rent_state', 'not in', ('not_booked', 'cancel')),
                ('rent_start_date', '<=', self.date_end),
                ('rent_end_date', '>=', self.date_start),
            ], order='rent_start_date desc', limit=1)

            lines_vals.append((0, 0, {
                'property_id': prop.id,
                'is_available': not bool(contract),
                'availability_status': 'available' if not contract else 'rented',
                'contract_id': contract.id if contract else False,
                'rent_start_date': contract.rent_start_date if contract else False,
                'rent_end_date': contract.rent_end_date if contract else False,
            }))

        self.line_ids = [(5, 0, 0)] + lines_vals

        return {
            'type': 'ir.actions.act_window',
            'name': f' {self.building_id.name} ({self.date_start} - {self.date_end})',
            'res_model': 'real.estate.property.availability.wizard.line',
            'view_mode': 'list',
            'domain': [('wizard_id', '=', self.id)],
            'target': 'current',
            "context": {
                "search_default_group_available": 1,
            },
        }



class RealEstatePropertyAvailabilityWizardLine(models.TransientModel):
    _name = 'real.estate.property.availability.wizard.line'
    _description = 'Property Availability Wizard Line'
    _order = 'is_available asc, property_id'

    wizard_id = fields.Many2one(
        'real.estate.property.availability.wizard',
        string='Wizard', required=True, ondelete='cascade',
    )
    property_id = fields.Many2one('account.analytic.account', string='Property', readonly=True)
    is_available = fields.Boolean(string='Available', readonly=True)
    contract_id = fields.Many2one('sale.order', string='Contract', readonly=True)
    rent_start_date = fields.Date(string='Contract Start', readonly=True)
    rent_end_date = fields.Date(string='Contract End', readonly=True)
    property_type = fields.Selection(
        related="property_id.property_type",
        string="Property Category",
        store=False,
        readonly=True,
    )
    availability_status = fields.Selection([
        ('available', 'Available'),
        ('rented', 'Rented'),
    ], string='Availability', readonly=True)


    def action_open_contract(self):
        self.ensure_one()
        if not self.contract_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rental Contract',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.contract_id.id,
            'target': 'current',
            'context': {'rental_mode': True},
        }
