/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

patch(ControlButtons.prototype, {
    async clickDiscount() {
        const config = this.pos.config;
        const limitEnabled = config.restrict_global_discount;
        const maxAllowed = config.max_global_discount;
        const order = this.pos.get_order();

        //the same subtotal as Odoo's global discount
        const subtotal = order.calculate_base_amount(
            order.get_orderlines().filter((line) => line.isGlobalDiscountApplicable())
        );

        this.dialog.add(NumberPopup, {
            title: _t("Discount Percentage"),
            startingValue: config.discount_pc,
            subtotal: subtotal,
            showAmountInput: true,
            getPayload: (num) => {
                const val = Math.max(
                    0,
                    Math.min(
                        100,
                        this.env.utils.parseValidFloat(num.toString())
                    )
                );

                if (limitEnabled && val > maxAllowed) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Discount Limit Exceeded"),
                        body: _t(
                            `You are not allowed to apply a discount greater than ${maxAllowed}%.`
                        ),
                    });
                    return;
                }

                this.apply_discount(val);
            },
        });
    },
});
