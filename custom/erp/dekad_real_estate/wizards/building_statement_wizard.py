from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BuildingStatementWizard(models.TransientModel):
    _name = 'building.statement.wizard'
    _description = 'Building Statement Filter'

    building_id = fields.Many2one(
        'real.estate.buildings',
        string='Building', required=True
    )

    property_ids = fields.Many2many(
        'account.analytic.account',
        string='Properties',
    )

    customer_id = fields.Many2one(
        'res.partner',
        string='Tenant',
    )

    start_date = fields.Date(string='Date')
    end_date = fields.Date(string='End Date')

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for wizard in self:
            if wizard.start_date and wizard.end_date and wizard.start_date > wizard.end_date:
                raise ValidationError("Start Date must be before or equal to End Date.")

    def action_apply_filter(self):
        self.ensure_one()

        domain = []

        if self.building_id:
            domain.append(('building_id', '=', self.building_id.id))

        if self.property_ids:
            domain.append(('property_id', 'in', self.property_ids.ids))

        if self.customer_id:
            domain.append(('customer_id', '=', self.customer_id.id))

        # rent_end_date must fall between start_date and end_date (inclusive)
        if self.start_date:
            domain.append(('rent_end_date', '>=', self.start_date))

        if self.end_date:
            domain.append(('rent_start_date', '<=', self.end_date))


        name = self.building_id.name if self.building_id else "Building Statement"

        if self.start_date and self.end_date:
            name = f"{name} {self.start_date} - {self.end_date}"
        elif self.start_date:
            name = f"{name} From {self.start_date}"
        elif self.end_date:
            name = f"{name} To {self.end_date}"

        return {
            'type': 'ir.actions.act_window',
            'name':name,
            'res_model': 'building.statement.line',
            'view_mode': 'list',
            'views': [(self.env.ref('dekad_real_estate.view_building_statement_line_list').id, 'list')],
            'search_view_id': [self.env.ref('dekad_real_estate.view_building_statement_line_search').id, 'search'],
            'domain': domain,
            'target': 'current',

            'context': {
                'statement_building_id': self.building_id.id or False,
                'statement_property_ids': self.property_ids.ids,
                'statement_customer_id': self.customer_id.id or False,
                'statement_start_date': self.start_date.isoformat() if self.start_date else False,
                'statement_end_date': self.end_date.isoformat() if self.end_date else False,
                'search_default_group_building': 1,
                'search_default_group_property': 1,
                'search_default_group_payment_state': 1,
            },
        }