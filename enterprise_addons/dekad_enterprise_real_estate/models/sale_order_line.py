from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    @api.constrains("start_date", "end_date", "order_id")
    def _check_line_date_range(self):
        for line in self:
            order = line.order_id

            if not line.start_date or not line.end_date:
                continue

            # 1. Line end >= line start
            if line.end_date < line.start_date:
                raise ValidationError(
                    "The line End Date must be greater than or equal to the Start Date."
                )

            # Skip if the contract dates are not set
            if not order.rental_start_date or not order.end_date:
                continue

            # 2 & 3. Line dates must be within the contract period
            if (
                line.start_date < order.rental_start_date
                or line.end_date > order.end_date
            ):
                raise ValidationError(
                    "The line dates must be within the contract period (%s to %s)."
                    % (order.rental_start_date, order.end_date)
                )