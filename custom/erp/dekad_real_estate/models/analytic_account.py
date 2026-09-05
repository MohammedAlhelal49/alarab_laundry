from odoo import models, fields,api
from datetime import date, timedelta
from odoo.exceptions import ValidationError


class PropertyType(models.Model):
    _name = 'property.type'
    _description = 'Property Type'

    name = fields.Char(required=True, string='Type Name', translate=True)

class PropertyOrientation(models.Model):
    _name = 'property.orientation'
    _description = 'Property Orientation'

    name = fields.Char(required=True, translate=True)


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    product_ids = fields.Many2many(
        'product.product',
        'account_analytic_account_product_rel',
        'analytic_account_id',
        'product_id',
        string='Related Products',
        help='Products associated with this property.',
        store=True,
    )

    property_address = fields.Text(
        string='Address',
        compute='_compute_property_address',
        store=True,
        readonly=True
    )

    property_image = fields.Binary(string='Property Image', store=True)

    property_type = fields.Selection(
        selection=[
            ('apartment', 'Apartment'),
            ('house', 'House'),
            ('studio', 'Studio'),
            ('office', 'Office'),
            ('commercial_space', 'Commercial space'),
            ('warehouse', 'Warehouse'),
            ('land', 'Land'),
            ('garage', 'Garage'),
            ('room', 'Room'),
            ('shed', 'Shabra'),
            ('shop', 'Shop'),
        ],
        string='Property Category',
        store=True,
    )

    property_type_id = fields.Many2one(
        'property.type',
        string='Property Type',
        help='Choose the type of property like 1 Bedroom, 2 Bedroom, etc.',
    )

    website_description = fields.Text(string='Description', store=True)

    is_property = fields.Boolean(
        string='Is Property',
        compute='_compute_is_property',
        store=True,
        readonly=True,
        copy=False,
    )

    invoice_status = fields.Selection(
        selection=[
            ('no', 'Nothing to invoice'),
            ('invoiced', 'Already invoiced'),
            ('to_invoice', 'To invoice'),
        ],
        string='Invoice Status',
        compute='_compute_invoice_status',
        store=True,
        readonly=True,
        copy=False,
    )

    is_published = fields.Boolean(string='Published', index=True, store=True)

    property_meter_reading_ids = fields.One2many(
        comodel_name='meter.reading',
        inverse_name='account_analytic_account_id',
        string='Meter Readings',
        store=True,
        copy=False,
    )

    property_building_id = fields.Many2one(
        comodel_name='real.estate.buildings',
        string='Building',
        store=True,
    )

    rental_contract_id = fields.One2many(
        comodel_name='sale.order',
        inverse_name='account_analytic_account_id',
        string='Rental Contracts',
        readonly=True,
    )
    rental_contract_ids_m2m = fields.Many2many(
        'sale.order',
        compute='_compute_rental_contract_ids_m2m',
        string='Contracts',
        store=False,
    )

    property_attachment_doc_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='real_estate_property_attachment_doc_rel',
        column1='account_analytic_account_id',
        column2='ir_attachment_id',
        string='Property Documents',
        copy=True,
        store=True,
    )

    property_attachment_image_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='real_estate_property_attachment_image_rel',
        column1='account_analytic_account_id',
        column2='ir_attachment_id',
        string='Property Images',
        copy=True,
        store=True,
    )


    rental_event_ids = fields.One2many(
        comodel_name='property.rental.event',
        inverse_name='property_id',
        string='Rental Events',
        order='start_date',

    )
    furnished = fields.Boolean(string='Furnished')

    floor_no = fields.Integer(
        string='Floor No',
        help='Floor number of the property inside the building'
    )

    bathroom_no = fields.Integer(
        string='Bathroom No',
        help='Number of bathrooms in the property'
    )

    bedroom_no = fields.Integer(
        string='Bedroom No',
        help='Number of bedrooms in the property'
    )

    is_property_sold = fields.Boolean(
        string='Sold',
        compute='_compute_is_property_sold',
        store=True,
        readonly=True,
    )

    @api.depends(
        'rental_contract_id.invoice_ids.state',
        'rental_contract_id.is_property_sale_contract'
    )
    def _compute_is_property_sold(self):
        for rec in self:
            sale_contracts = rec.rental_contract_id.filtered(
                lambda o: o.is_property_sale_contract
            )

            is_sold = False
            for order in sale_contracts:
                posted_invoices = order.invoice_ids.filtered(
                    lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
                )
                if posted_invoices:
                    is_sold = True
                    break

            rec.is_property_sold = is_sold

    @api.depends('plan_id')
    def _compute_is_property(self):
        property_plan = self.env.ref('dekad_real_estate.analytic_plan_properties', raise_if_not_found=False)
        for property in self:
            property.is_property = property.plan_id == property_plan

    @api.depends('property_meter_reading_ids.usage', 'property_meter_reading_ids.invoice_id')
    def _compute_invoice_status(self):
        for record in self:
            meter_readings = record.property_meter_reading_ids.filtered(lambda l: l.usage > 0)
            if not meter_readings:
                record.invoice_status = 'no'
            elif not meter_readings.filtered(lambda l: not l.invoice_id):
                record.invoice_status = 'invoiced'
            else:
                record.invoice_status = 'to_invoice'

    def action_create_invoice(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_move_type': 'out_invoice',
                'default_partner_id': self.partner_id.id if self.partner_id else False,
                'default_invoice_origin': self.name,
            },
        }

    user_id = fields.Many2one('res.users', 'Organizer', default=lambda self: self.env.user)
    fiscal_country_codes = fields.Char(
        string="Fiscal Country Codes",
        help="Dummy field for Owl frontend compatibility",
        store=False,
    )
    parent_id = fields.Many2one(
        'account.analytic.account',
        string='Parent Property',
        help='Dummy field for filter compatibility. Not used in logic.',
        ondelete='cascade'
    )
    email = fields.Char(
        string='Email',
        help='Dummy email field for Owl widget compatibility.'
    )
    phone_mobile_search = fields.Char(
        string='Phone or Mobile',
        help='Dummy field for Owl filter compatibility.'
    )
    category_id = fields.Many2one(
        'res.partner.category',
        string='Category',
        help='Dummy category for Owl filter compatibility'
    )

    is_available = fields.Boolean(
        string="Available",
        compute='_compute_is_available',
        store=True,
    )

    @api.depends(
        'rental_contract_id.rent_state',
        'rental_contract_id.rent_start_date',
        'rental_contract_id.rent_end_date',
        'rental_contract_id.is_closed',
    )
    def _compute_is_available(self):
        today = date.today()
        for rec in self:
            contracts = rec.rental_contract_id
            has_active = contracts.filtered(
                lambda c: c.rent_state in ('booked', 'paid', 'not_paid', 'partially_paid')
                          and not c.is_closed
                          and c.rent_start_date and c.rent_start_date <= today
                          and c.rent_end_date and c.rent_end_date >= today
            )
            rec.is_available = not bool(has_active)


    rental_event_ids = fields.One2many(
        'property.rental.event', 'property_id', string='Rental Events'
    )

    rental_event_count = fields.Integer(
        string='Rental Event',
        compute='_compute_rental_event_count'
    )

    show_rental_event_button = fields.Boolean(
        compute='_compute_show_rental_event_button'
    )

    @api.depends('rental_event_ids')
    def _compute_rental_event_count(self):
        for rec in self:
            rec.rental_event_count = len(rec.rental_event_ids)

    @api.depends('rental_event_count')
    def _compute_show_rental_event_button(self):
        for rec in self:
            rec.show_rental_event_button = rec.rental_event_count > 0

    def action_open_property_rental_events(self):
        self.ensure_one()
        filter_model = self.env['property.rental.filter']

        user_filter = filter_model.search([
            ('user_id', '=', self.env.uid),
            ('property_id', '=', self.id)
        ], limit=1)

        if not user_filter:
            filter_model.create({
                'user_id': self.env.uid,
                'property_id': self.id,
                'property_checked': True,
            })
        else:
            user_filter.property_checked = True

        filter_model.search([
            ('user_id', '=', self.env.uid),
            ('property_id', '!=', self.id)
        ]).write({'property_checked': False})

        return {
            'type': 'ir.actions.act_window',
            'name': 'Rental Events',
            'res_model': 'property.rental.event',
            'view_mode': 'calendar,list,form',
            'views': [
                (self.env.ref('dekad_real_estate.view_property_rental_event_calendar').id, 'calendar'),
                (self.env.ref('dekad_real_estate.view_property_rental_event_list').id, 'list'),
                (self.env.ref('dekad_real_estate.view_property_rental_event_form').id, 'form'),
            ],
            'search_view_id': self.env.ref('dekad_real_estate.view_property_rental_event_search').id,
            'target': 'current',
            'context': {},
        }

    @api.depends(
        'property_building_id',
        'property_building_id.street',
        'property_building_id.street2',
        'property_building_id.city',
        'property_building_id.state',
        'property_building_id.country',
        'property_building_id.zip',
    )
    def _compute_property_address(self):
        for rec in self:
            if not rec.property_building_id:
                rec.property_address = False
                continue

            building = rec.property_building_id
            address_parts = []

            if building.street:
                address_parts.append(building.street)
            if building.street2:
                address_parts.append(building.street2)
            if building.city:
                address_parts.append(building.city)
            if building.state:
                address_parts.append(building.state.name)
            if building.country:
                address_parts.append(building.country.name)
            if building.zip:
                address_parts.append(building.zip)

            rec.property_address = ', '.join(address_parts)


    @api.constrains('floor_no', 'property_building_id')
    def _check_floor_no(self):
        for rec in self:
            if not rec.property_building_id or rec.floor_no is False:
                continue

            max_floors = rec.property_building_id.number_of_floors

            if rec.floor_no < 0:
                raise ValidationError("Floor number cannot be less than 0.")

            if rec.floor_no > max_floors:
                raise ValidationError(
                    f"Invalid floor number: Building '{rec.property_building_id.name}' "
                    f"has only {max_floors} floor(s)."
                )


    @api.depends('rental_contract_id')
    def _compute_rental_contract_ids_m2m(self):
        for rec in self:
            rec.rental_contract_ids_m2m = rec.rental_contract_id

    offer_type = fields.Selection(
        selection=[
            ('sale', 'For Sale'),
            ('rent', 'For Rent'),
        ],
        string='Offer Type',
        default='rent',
        required=True,
        store=True,
        help='Specify whether the property is available for Sale or Rent.'
    )

    def unlink(self):
        for rec in self:
            # Block deletion if linked to contracts
            if rec.rental_contract_id:
                raise ValidationError(
                    "You cannot delete this property because it is linked to rental or sale contracts."
                )

            # Block deletion if linked to meter readings
            if rec.property_meter_reading_ids:
                raise ValidationError(
                    "You cannot delete this property because it has meter readings."
                )

            # Block deletion if linked to rental events
            if rec.rental_event_ids:
                raise ValidationError(
                    "You cannot delete this property because it has rental events."
                )

            # Block deletion if invoices exist
            if rec.invoice_status in ('invoiced', 'to_invoice'):
                raise ValidationError(
                    "You cannot delete this property because it has invoices."
                )

        return super().unlink()

    apartment_area = fields.Float(
        string='Apartment Area (sqm)',
        help='Total area of the apartment in square meters.'
    )

    apartment_orientation_ids = fields.Many2many(
        'property.orientation',
        'account_analytic_orientation_rel',
        'analytic_account_id',
        'orientation_id',
        string='Orientation',
        help='Directions the apartment faces (e.g., East, West, etc.).'
    )

    show_offer_type = fields.Boolean(
        string="Show Offer Type",
        compute='_compute_show_offer_type',
        store=False,
    )

    @api.depends('company_id.enable_sale_properties')
    def _compute_show_offer_type(self):
        for rec in self:
            rec.show_offer_type = rec.company_id.enable_sale_properties


    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._update_product_types_if_rent()
        return record

    def write(self, vals):
        res = super().write(vals)
        self._update_product_types_if_rent()
        return res

    def _update_product_types_if_rent(self):
        for rec in self:
            if rec.offer_type == 'rent' and rec.product_ids:
                service_templates = rec.product_ids.mapped('product_tmpl_id').filtered(
                    lambda tmpl: tmpl.type != 'service'
                )
                if service_templates:
                    service_templates.write({'type': 'service'})

