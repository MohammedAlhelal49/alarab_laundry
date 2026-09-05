/** @odoo-module */
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(OrderSummary.prototype, {
    async setLinePrice(line, price) {
        if (this.pos.cashierHasPriceControlRights()) {
            line.price_type = "manual";
            line.set_unit_price(price);
            return;
        }
        this.dialog.add(AlertDialog, {
            title: _t("Access Denied"),
            body: _t("You are not allowed to change the price of a product."),
        });
    },
});