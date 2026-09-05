from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import date


class PropertyRentHistory(models.Model):
    _name = "property.rent.history"
    _description = "Property Rent History"
    _order = "year desc"

    property_id = fields.Many2one(
        "account.analytic.account",
        required=True,
        ondelete="cascade",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="property_id.currency_id",
        store=True,
        readonly=True,
    )

    def _year_selection(self):
        current = date.today().year
        return [
            (str(y), str(y))
            for y in range(current - 11, current + 11)
        ]

    year = fields.Selection(
        selection=_year_selection,
        string="Year",
        required=True,
    )

    annual_rent = fields.Monetary(
        string="Annual Rent",
        currency_field="currency_id",
        required=True,
    )

    security_deposit = fields.Monetary(
        string="Security Deposit",
        currency_field="currency_id",
        required=True,
    )

    _sql_constraints = [
        (
            "property_year_unique",
            "unique(property_id, year)",
            "A rent record already exists for this year.",
        )
    ]


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    # -------------------------------------------------------------------------
    # Property Fields
    # -------------------------------------------------------------------------

    property_image = fields.Image(
        string="Property Image",
    )

    is_published = fields.Boolean(
        string="Published",
        index=True,
    )

    status = fields.Selection(
        [
            ("vacant", "Vacant"),
            ("occupied", "Occupied"),
            ("on_hold", "On Hold"),
            ("under_maintenance", "Under Maintenance"),
        ],
        string="Status",
        default="vacant",
        readonly=True,
        store=True,
    )

    manual_status = fields.Selection(
        [
            ("on_hold", "On Hold"),
            ("under_maintenance", "Under Maintenance"),
        ],
        string="Manual Status",
    )

    is_property = fields.Boolean(
        string="Is Property",
        compute="_compute_is_property",
        store=True,
        readonly=True,
    )

    analytical_account = fields.Many2one(
        "account.analytic.account",
        string="Analytical Account",
        ondelete="set null",
        default=lambda self: self,
    )

    analytical_plan_id = fields.Many2one(
        "account.analytic.plan",
        string="Analytical Plan",
        related="plan_id",
    )

    property_building_id = fields.Many2one(
        "real.estate.building",
        string="Building",
    )

    rental_contract_id = fields.Many2one(
        "sale.order",
        string="Rental Contract",
        readonly=True,
        store=True,
        ondelete="set null",
    )

    property_address = fields.Text(
        string="Address",
        compute="_compute_property_address",
        store=True,
    )

    property_type = fields.Selection(
        [
            ("Appartment", "Appartment"),
            ("House", "House"),
            ("Studio", "Studio"),
            ("Office", "Office"),
            ("Commercial space", "Commercial space"),
            ("Warehouse", "Warehouse"),
            ("Land", "Land"),
            ("Garage", "Garage"),
            ("Room", "Room"),
        ],
        string="Property Type",
    )

    invoice_status = fields.Selection(
        [
            ("no", "Nothing to invoice"),
            ("invoiced", "Already invoiced"),
            ("to_invoice", "To invoice"),
        ],
        string="Invoice Status",
        compute="_compute_invoice_status",
        store=True,
        readonly=True,
    )

    category = fields.Char(
        string="Category",
    )

    unit_type_id = fields.Char(
        string="Unit Type ID",
    )

    unit_status_id = fields.Char(
        string="Unit Status ID",
    )

    bedroom_no = fields.Selection(
        [
            ("0", "0"),
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
            ("1.5", "1.5"),
            ("Studio", "Studio"),
        ],
        string="BedRoom No",
    )

    area_size = fields.Char(
        string="Area Size",
    )

    website_description = fields.Text(
        string="Description",
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

    property_meter_reading_ids = fields.One2many(
        "meter.reading",
        "account_analytic_account_id",
        string="Meter Readings",
    )

    rent_history_ids = fields.One2many(
        "property.rent.history",
        "property_id",
        string="Rent History",
    )


    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    @api.depends("plan_id")
    def _compute_is_property(self):
        property_plan = self.env.ref(
            "dekad_enterprise_real_estate.analytic_plan_properties",
            raise_if_not_found=False,
        )

        for record in self:
            record.is_property = bool(
                property_plan and record.plan_id == property_plan
            )


    @api.depends(
        "property_meter_reading_ids.usage",
        "property_meter_reading_ids.invoice_id",
    )
    def _compute_invoice_status(self):
        for record in self:
            readings = record.property_meter_reading_ids.filtered(
                lambda r: r.usage > 0
            )

            if not readings:
                record.invoice_status = "no"

            elif not readings.filtered(
                lambda r: not r.invoice_id
            ):
                record.invoice_status = "invoiced"

            else:
                record.invoice_status = "to_invoice"

    def write(self, vals):
        if "manual_status" in vals:

            if vals["manual_status"]:
                vals["status"] = vals["manual_status"]
            else:
                vals["status"] = "vacant"

        return super().write(vals)




    @api.depends(
        "property_building_id",
        "property_building_id.street",
        "property_building_id.street2",
        "property_building_id.city",
        "property_building_id.state_id",
        "property_building_id.country_id",
        "property_building_id.zip",
    )
    def _compute_property_address(self):
        for record in self:
            building = record.property_building_id

            if not building:
                record.property_address = False
                continue

            address = []

            if building.street:
                address.append(building.street)

            if building.street2:
                address.append(building.street2)

            if building.city:
                address.append(building.city)

            if building.state_id:
                address.append(building.state_id.name)

            if building.country_id:
                address.append(building.country_id.name)

            if building.zip:
                address.append(building.zip)

            record.property_address = ", ".join(address)

    # -------------------------------------------------------------------------
    # TODO
    # -------------------------------------------------------------------------

    #
    # The Studio form references these existing methods/fields:
    #
    #   action_view_invoice()
    #   action_view_vendor_bill()
    #   subscriptions_action()
    #   invoice_count
    #   vendor_bill_count
    #   subscription_count
    #
    # Implement them later if they don't already exist in another inherited
    # module.
    #