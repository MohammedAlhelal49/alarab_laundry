from odoo import models, fields, api


class ContractReportWizard(models.TransientModel):
    _name = 'contract.report.wizard'
    _description = 'Contract Report Wizard'

    building_id = fields.Many2one('real.estate.buildings', required=True)
    property_id = fields.Many2one('account.analytic.account')
    date_from = fields.Date()
    date_to = fields.Date()


    @api.onchange('building_id')
    def _onchange_building_id(self):
        if self.building_id:
            return {
                'domain': {
                    'property_id': [
                        ('property_building_id', '=', self.building_id.id),
                        ('is_property', '=', True)
                    ]
                }
            }

    def action_show_report(self):
        self.ensure_one()

        # Clear old report data
        self.env["contract.report"].search([]).unlink()

        # Build search domain
        domain = [
            ("state", "in", ["sale", "cancel"]),
            ("cancel_type", "!=", "paid_cancel"),
            ("account_analytic_account_id.property_building_id", "=", self.building_id.id),

        ]

        if self.property_id:
            domain.append(
                ("account_analytic_account_id", "=", self.property_id.id)
            )

        if self.date_from and self.date_to:
            domain.extend([
                ("rent_start_date", "<=", self.date_to),
                ("rent_end_date", ">=", self.date_from),
            ])
        elif self.date_from:
            domain.append(
                ("rent_end_date", ">=", self.date_from)
            )
        elif self.date_to:
            domain.append(
                ("rent_start_date", "<=", self.date_to)
            )

        contracts = self.env["sale.order"].search(
            domain,
            order="rent_start_date asc",
        )

        vals_list = []

        for c in contracts:
            transfer = booking = aquda = airbnb = cash = 0

            for line in c.payment_info_ids:
                amount = line.amount or 0
                category = line.payment_method_line_id.real_estate_payment_category

                if category == "bank_transfer":
                    transfer += amount
                elif category == "booking":
                    booking += amount
                elif category == "aquda":
                    aquda += amount
                elif category == "airbnb":
                    airbnb += amount
                elif category == "cash":
                    cash += amount

            vals_list.append({
                "contract_date": c.rent_start_date,
                "partner_id": c.partner_id.id,
                "note": c.note,
                "bank_transfer": transfer,
                "booking": booking,
                "aquda": aquda,
                "airbnb": airbnb,
                "cash": cash,
                "currency_id": c.currency_id.id,
                "cancel_type": c.cancel_type,
            })

        if vals_list:
            self.env["contract.report"].create(vals_list)

        # Report name
        report_name = self.building_id.display_name

        if self.property_id:
            report_name += f" - {self.property_id.display_name}"

        if self.date_from or self.date_to:
            if self.date_from and self.date_to:
                report_name += (
                    f" ({self.date_from.strftime('%d/%m/%Y')} → "
                    f"{self.date_to.strftime('%d/%m/%Y')})"
                )
            elif self.date_from:
                report_name += (
                    f" (From {self.date_from.strftime('%d/%m/%Y')})"
                )
            else:
                report_name += (
                    f" (Until {self.date_to.strftime('%d/%m/%Y')})"
                )

        return {
            "type": "ir.actions.act_window",
            "name": report_name,
            "res_model": "contract.report",
            "view_mode": "list",
            "target": "current",
        }