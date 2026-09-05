from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_amount


class SaleOrder(models.Model):
    _inherit = "sale.order"

    contract_number = fields.Char(
        string="Contract Number",
        copy=False,
    )

    rental_start_date = fields.Date(
        string="Rental Start Date",
    )

    annual_rental = fields.Float(
        string="Annual Rent",
        readonly=True,
    )

    sd = fields.Float(
        string="Security Deposit",
        readonly=True,
    )

    account_analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Property",
        domain="[('is_property', '=', True), ('property_building_id', '=', building_id)]",
        ondelete="set null",
    )

    building_id = fields.Many2one(
        "real.estate.building",
        string="Building",
    )

    related_building_id = fields.Many2one(
        "real.estate.building",
        string="Building",
        related="account_analytic_account_id.property_building_id",
        store=True,
        readonly=True,
    )

    guarant_partner_id = fields.Many2one(
        "res.partner",
        string="Guarantor",
    )

    meter_reading_ids = fields.One2many(
        "meter.reading",
        "sale_order_id",
        string="Meter Readings",
    )

    contract_status = fields.Selection(
        [
            ("Posted", "Posted"),
            ("Expired", "Expired"),
            ("notice", "Notice"),
            ("Legal Case", "Legal Case"),
            ("On Hold", "On Hold"),
        ],
        string="Contract Status",
    )

    notice_date = fields.Date(
        string="Notice Date",
    )
    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_rent_history(self):
        self.ensure_one()

        if not self.account_analytic_account_id or not self.rental_start_date:
            return self.env["property.rent.history"]

        contract_year = str(self.rental_start_date.year)

        return self.env["property.rent.history"].search(
            [
                ("property_id", "=", self.account_analytic_account_id.id),
                ("year", "=", contract_year),
            ],
            limit=1,
        )


    def _update_rent_values(self):
        for rec in self:
            history = rec._get_rent_history()

            if history:
                rec.annual_rental = history.annual_rent
                rec.sd = history.security_deposit
            else:
                rec.annual_rental = 0.0
                rec.sd = 0.0

    # -------------------------------------------------------------------------
    # Onchange
    # -------------------------------------------------------------------------

    @api.onchange("account_analytic_account_id", "rental_start_date")
    def _onchange_property_year(self):
        self._update_rent_values()

    # -------------------------------------------------------------------------
    # Create / Write
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_rent_values()
        return records


    # -------------------------------------------------------------------------
    # Validations
    # -------------------------------------------------------------------------

    @api.constrains("account_analytic_account_id", "rental_start_date")
    def _check_rent_history(self):
        for rec in self:
            if not rec.account_analytic_account_id or not rec.rental_start_date:
                continue

            if not rec._get_rent_history():
                raise ValidationError(
                    "No Rent History exists for year %s. "
                    "Please add a Rent History record before creating the rental contract."
                    % rec.rental_start_date.year
                )

    @api.constrains(
        "amount_untaxed",
        "rental_start_date",
        "end_date",
        "account_analytic_account_id",
    )
    def _check_minimum_rent(self):
        for rec in self:

            if (
                not rec.account_analytic_account_id
                or not rec.rental_start_date
                or not rec.end_date
            ):
                continue

            if rec.end_date < rec.rental_start_date:
                raise ValidationError(
                    "Contract End Date must be after Rental Start Date."
                )

            history = rec._get_rent_history()

            if not history:
                continue

            months = (
                (rec.end_date.year - rec.rental_start_date.year) * 12
                + rec.end_date.month
                - rec.rental_start_date.month
                + 1
            )

            minimum_rent = history.annual_rent * months / 12

            # Compare against the Sale Order total
            contract_rent = rec.amount_untaxed

            if contract_rent < minimum_rent:

                if rec.env.user.has_group(
                    "alqatara_implementation.group_authorizer"
                ):

                    self.env.user._bus_send(
                        "simple_notification",
                        {
                            "title": "Minimum Rent Warning",
                            "message": (
                                           "The contract total (%s) is below the minimum "
                                           "allowed rent (%s).\n\n"
                                           "You are allowed to approve this contract because "
                                           "you belong to the Authorizer group."
                                       )
                                       % (
                                           format_amount(
                                               self.env,
                                               contract_rent,
                                               rec.currency_id,
                                           ),
                                           format_amount(
                                               self.env,
                                               minimum_rent,
                                               rec.currency_id,
                                           ),
                                       ),
                            "type": "warning",
                                "sticky": True,
                        },
                    )

                else:
                    raise ValidationError(
                        "The contract total (%s) is below the minimum allowed rent (%s). "
                        "Only users in the Authorizer group can approve a contract below "
                        "the minimum rent."
                        % (
                            format_amount(
                                self.env,
                                contract_rent,
                                rec.currency_id,
                            ),
                            format_amount(
                                self.env,
                                minimum_rent,
                                rec.currency_id,
                            ),
                        )
                    )


    def _prepare_upsell_renew_order_values(self, subscription_state):
        vals = super()._prepare_upsell_renew_order_values(subscription_state)

        vals.update({
            "rental_start_date": self.rental_start_date,
            "contract_number": self.contract_number,
            "annual_rental": self.annual_rental,
            "sd": self.sd,
            "account_analytic_account_id": self.account_analytic_account_id.id,
            "building_id": self.building_id.id,
            "guarant_partner_id": self.guarant_partner_id.id,
        })

        return vals

    def action_confirm(self):
        res = super().action_confirm()

        for order in self:
            if order.account_analytic_account_id:
                order.account_analytic_account_id.write({
                    "status": "occupied",
                    "rental_contract_id": order.id,
                })

        return res


    def action_cancel(self):
        res = super().action_cancel()

        for order in self:
            if order.account_analytic_account_id:
                property = order.account_analytic_account_id
                if property.rental_contract_id == order:
                    property.write({
                        "status": "vacant",
                        "manual_status": False,
                        "rental_contract_id": False,
                    })

        return res


    def write(self, vals):
        res = super().write(vals)

        if "account_analytic_account_id" in vals or "rental_start_date" in vals:
            self._update_rent_values()

        if "subscription_state" in vals:
            for order in self.filtered(lambda o: o.subscription_state == "6_churn"):
                if order.account_analytic_account_id:
                    property = order.account_analytic_account_id
                    property.write({
                        "status": "vacant",
                        "manual_status": False,
                        "rental_contract_id": False,
                    })

        return res