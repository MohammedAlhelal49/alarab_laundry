from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()

        authorizer_group = self.env.ref(
            "alqatara_implementation.group_authorizer"
        )

        current_user = self.env.user

        for move in self:
            if move.move_type != "out_invoice":
                continue

            sale_orders = move.invoice_line_ids.sale_line_ids.order_id

            for order in sale_orders:
                for user in authorizer_group.users:
                    order.activity_schedule(
                        "mail.mail_activity_data_todo",
                        user_id=user.id,
                        summary="Review Customer Invoice",
                        note=(
                            f"The customer invoice has been confirmed by "
                            f"{current_user.name}. Please review it."
                        ),
                    )

        return res