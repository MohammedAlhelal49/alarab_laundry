from odoo import models
from odoo.exceptions import AccessError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        res = super().action_confirm()

        checker_group = self.env.ref(
            "alqatara_implementation.group_checker"
        )

        current_user = self.env.user

        for order in self:
            for user in checker_group.users:
                order.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=user.id,
                    summary="Create Customer Invoice",
                    note=f"Sale Order has been confirmed by {current_user.name}. Please create and confirm the invoice.",
                )

        return res