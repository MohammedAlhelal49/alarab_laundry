from odoo import models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def _visible_menu_ids(self, debug=False):
        visible_ids = super()._visible_menu_ids(debug=debug)

        if self.env.user.has_group("dekad_reception_management.group_reception"):

            hidden_ids = set()

            sale_menu = self.env.ref(
                "sale.sale_menu_root",
                raise_if_not_found=False,
            )
            if sale_menu:
                hidden_ids.add(sale_menu.id)

            accounting_menu = self.env.ref(
                "accountant.menu_accounting",
                raise_if_not_found=False,
            )
            if accounting_menu:
                hidden_ids.add(accounting_menu.id)

            visible_ids -= hidden_ids

        return visible_ids