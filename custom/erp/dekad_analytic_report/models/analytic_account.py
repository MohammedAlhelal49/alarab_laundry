from odoo import _, models
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    def unlink(self):
        for analytic in self:
            usages = analytic._get_protected_document_usages()

            if usages:
                details = '\n'.join(
                    f"• {usage}"
                    for usage in usages
                )

                raise UserError(
                    _(
                        "You cannot delete the analytic account "
                        "'%(analytic)s'.\n\n"
                        "It is used by confirmed/posted documents:\n\n"
                        "%(documents)s\n\n"
                        "Archive the analytic account instead of deleting it."
                    ) % {
                        'analytic': analytic.display_name,
                        'documents': details,
                    }
                )

        return super().unlink()

    def _get_protected_document_usages(self):
        self.ensure_one()

        usages = []

        # =========================================================
        # Accounting
        # =========================================================
        usages += self._get_account_move_usages()

        # =========================================================
        # Purchase
        # =========================================================
        usages += self._get_purchase_order_usages()

        # =========================================================
        # Sales
        # =========================================================
        usages += self._get_sale_order_usages()

        return usages

    def _get_account_move_usages(self):
        self.ensure_one()

        self.env.cr.execute(
            """
            SELECT DISTINCT
                   am.id,
                   am.name,
                   am.state,
                   am.move_type
              FROM account_move_line aml
              JOIN account_move am
                ON am.id = aml.move_id

             WHERE aml.analytic_distribution IS NOT NULL

               AND am.state != 'draft'

               AND EXISTS (
                    SELECT 1
                      FROM jsonb_object_keys(
                           aml.analytic_distribution
                      ) AS analytic_key

                     WHERE %s = ANY(
                         string_to_array(
                             analytic_key,
                             ','
                         )
                     )
               )

             ORDER BY am.id

             LIMIT 20
            """,
            (str(self.id),)
        )

        usages = []

        for move_id, name, state, move_type in self.env.cr.fetchall():

            document_name = name or str(move_id)

            usages.append(
                _(
                    "Accounting: %(document)s "
                    "[%(state)s]"
                ) % {
                    'document': document_name,
                    'state': state,
                }
            )

        return usages

    def _get_purchase_order_usages(self):
        self.ensure_one()

        self.env.cr.execute(
            """
            SELECT DISTINCT
                   po.id,
                   po.name,
                   po.state

              FROM purchase_order_line pol

              JOIN purchase_order po
                ON po.id = pol.order_id

             WHERE pol.analytic_distribution IS NOT NULL

               AND po.state != 'draft'

               AND EXISTS (
                    SELECT 1
                      FROM jsonb_object_keys(
                           pol.analytic_distribution
                      ) AS analytic_key

                     WHERE %s = ANY(
                         string_to_array(
                             analytic_key,
                             ','
                         )
                     )
               )

             ORDER BY po.id

             LIMIT 20
            """,
            (str(self.id),)
        )

        usages = []

        for order_id, name, state in self.env.cr.fetchall():

            usages.append(
                _(
                    "Purchase Order: %(document)s "
                    "[%(state)s]"
                ) % {
                    'document': name or str(order_id),
                    'state': state,
                }
            )

        return usages

    def _get_sale_order_usages(self):
        self.ensure_one()

        self.env.cr.execute(
            """
            SELECT DISTINCT
                   so.id,
                   so.name,
                   so.state

              FROM sale_order_line sol

              JOIN sale_order so
                ON so.id = sol.order_id

             WHERE sol.analytic_distribution IS NOT NULL

               AND so.state != 'draft'

               AND EXISTS (
                    SELECT 1
                      FROM jsonb_object_keys(
                           sol.analytic_distribution
                      ) AS analytic_key

                     WHERE %s = ANY(
                         string_to_array(
                             analytic_key,
                             ','
                         )
                     )
               )

             ORDER BY so.id

             LIMIT 20
            """,
            (str(self.id),)
        )

        usages = []

        for order_id, name, state in self.env.cr.fetchall():

            usages.append(
                _(
                    "Sales Order: %(document)s "
                    "[%(state)s]"
                ) % {
                    'document': name or str(order_id),
                    'state': state,
                }
            )

        return usages