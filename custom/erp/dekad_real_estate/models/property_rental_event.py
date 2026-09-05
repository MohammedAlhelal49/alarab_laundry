from odoo import models, fields,api
from odoo.exceptions import ValidationError
from datetime import timedelta



class PropertyRentalEvent(models.Model):
    _name = 'property.rental.event'
    _description = 'Property Rental Event'
    _rec_name = 'name'
    _order = ('start_date, property_id')

    name = fields.Char(compute='_compute_name', store=True)

    property_id = fields.Many2one(
        'account.analytic.account',
        string='Property',
        domain="[('is_property', '=', True)]",
        required=True,
        ondelete='restrict'
    )

    multi_property_ids=fields.Many2many(
        'account.analytic.account',
        string='Properties',
        domain="[('is_property', '=', True)]",
        relation='property_rental_event_multi_property_rel',  # <-- Add this!
    )

    property_ids = fields.Many2many(
        'account.analytic.account',
        compute='_compute_property_ids',
        string='Property Filter Helper',
        store=True,
        relation='property_rental_event_filter_rel',  # Optional, good for clarity

    )

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date')
    description = fields.Text(string='Notes')
    cost = fields.Monetary(string='Price')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id.id
    )

    @api.depends('property_id')
    def _compute_property_ids(self):
        for rec in self:
            rec.property_ids = rec.property_id


    @api.depends('property_id.name', 'cost', 'currency_id')
    def _compute_name(self):
        for rec in self:
            prop = rec.property_id.name or "Property"
            cost = rec.cost or 0
            symbol = rec.currency_id.symbol or ""

            if cost:
                rec.name = f"{prop} - {cost} {symbol}"
            else:
                rec.name = prop

    @api.constrains('property_id', 'start_date')
    def _check_duplicate_event(self):
        for rec in self:
            if not rec.property_id or not rec.start_date:
                continue

            conflict = self.search([
                ('id', '!=', rec.id),
                ('property_id', '=', rec.property_id.id),
                ('start_date', '=', rec.start_date)
            ], limit=1)

            if conflict:
                raise ValidationError(
                    f"There is already a rental event for '{rec.property_id.name}' on {rec.start_date}."
                )

    def unlink(self):
        SaleOrder = self.env['sale.order']

        for rec in self:
            if not rec.property_id:
                continue

            linked_orders = SaleOrder.search([
                ('account_analytic_account_id', '=', rec.property_id.id),
                ('rent_start_date', '<=', rec.end_date or rec.start_date),
                ('rent_end_date', '>=', rec.start_date),
                ('state', 'in', ['sale', 'done']),
            ])

            if linked_orders:
                raise ValidationError(
                    f"Cannot delete rental event '{rec.name}' because it is linked to rental orders: "
                    f"{', '.join(linked_orders.mapped('name'))}"
                )

        return super(PropertyRentalEvent, self).unlink()

    @api.model
    def create(self, vals):
        start_date = fields.Date.from_string(vals.get('start_date'))
        end_date = fields.Date.from_string(vals.get('end_date')) or start_date

        if start_date > end_date:
            raise ValidationError("End date cannot be before start date.")

        # Safely extract property IDs from Many2many command
        m2m_commands = vals.get('multi_property_ids') or []
        property_ids = []
        for cmd in m2m_commands:
            if cmd[0] == 6:  # replace all
                property_ids = cmd[2]
            elif cmd[0] == 4:  # add
                property_ids.append(cmd[1])

        if not property_ids:
            raise ValidationError("Please select at least one property.")

        records = []
        for property_id in property_ids:
            current_date = start_date
            while current_date <= end_date:
                vals_copy = vals.copy()

                # Assign a single property to the new record
                vals_copy['property_id'] = property_id
                vals_copy['multi_property_ids'] = False  # do not store the multi-selection
                vals_copy['start_date'] = current_date
                vals_copy['end_date'] = current_date

                records.append(super(PropertyRentalEvent, self).create(vals_copy))
                current_date += timedelta(days=1)

        return records[0] if len(records) == 1 else self.browse([r.id for r in records])



class PropertyRentalFilter(models.Model):
    _name = 'property.rental.filter'
    _description = 'Rental Event Property Filter'

    user_id = fields.Many2one('res.users', 'Me', required=True, default=lambda self: self.env.user, index=True, ondelete='cascade')


    property_id = fields.Many2one(
        'account.analytic.account', string='Property',
        domain="[('is_property', '=', True)]", required=True
    )

    property_checked = fields.Boolean(string='Checked', default=True)
    parent_id = fields.Many2one('property.rental.filter', string='Parent', ondelete='cascade')

    _sql_constraints = [
        ('user_property_unique', 'UNIQUE(user_id, property_id)',
         'A user cannot have the same property twice.')
    ]

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        default_prop_id = self.env.context.get('default_property_filter_property_id')
        if default_prop_id:
            already_exists = self.search([
                ('user_id', '=', self.env.uid),
                ('property_id', '=', default_prop_id),
            ], limit=1)
            if not already_exists:
                self.create({
                    'user_id': self.env.uid,
                    'property_id': default_prop_id,
                    'property_checked': True,
                })
        return res
