from odoo import fields, models


class Building(models.Model):
    _name = "real.estate.building"
    _description = "Building"
    _rec_name = "name"
    _order = "id"

    name = fields.Char(required=True)

    street = fields.Char()
    street2 = fields.Char()
    city = fields.Char()

    state_id = fields.Many2one(
        "res.country.state",
        string="State",
    )

    zip = fields.Char()

    country_id = fields.Many2one(
        "res.country",
        string="Country",
    )

    land_lord = fields.Char()

    plot_number = fields.Char()

    no_of_floors = fields.Char()

    no_of_stores = fields.Char()

    no_of_residential_flat = fields.Char()

    no_of_commercial_flat = fields.Char()

    total_units = fields.Char()