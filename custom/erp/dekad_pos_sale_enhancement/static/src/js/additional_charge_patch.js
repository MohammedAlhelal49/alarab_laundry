/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
patch(ControlButtons.prototype, {
    async clickAdditionalCharge() {
        const order = this.pos.get_order();
        const subtotal = order.calculate_base_amount(
            order.get_orderlines().filter((line) => line.isGlobalDiscountApplicable())
        );
        this.dialog.add(NumberPopup, {
            title: _t("Additional Charge"),
            startingValue: this.pos.config.additional_charge_percent || 0,
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
                this.applyAdditionalCharge(val);
            },
        });
    },
    async applyAdditionalCharge(pc) {
        const order = this.pos.get_order();
        const product = this.pos.config.additional_charge_product_id;
        if (!product) {
            this.dialog.add(AlertDialog, {
                title: _t("No Additional Charge Product"),
                body: _t(
                    "Please configure an Additional Charge Product in the POS settings."
                ),
            });
            return;
        }
        // Remove previous additional charge lines
        order.get_orderlines()
            .filter((line) => line.get_product() === product)
            .forEach((line) => line.delete());
        // Same logic as Odoo Global Discount
        const linesByTax = order.get_orderlines_grouped_by_tax_ids();
        for (const [tax_ids, lines] of Object.entries(linesByTax)) {
            const taxIds = tax_ids
                .split(",")
                .filter((id) => id !== "")
                .map(Number);
            const baseAmount = order.calculate_base_amount(
                lines.filter((line) => line.isGlobalDiscountApplicable())
            );
            if (baseAmount <= 0) {
                continue;
            }
            const taxes = taxIds
                .map((id) => this.pos.models["account.tax"].get(id))
                .filter(Boolean);
            // Positive instead of negative
            const additional = (pc / 100) * baseAmount;
            if (additional <= 0) {
                continue;
            }
            await this.pos.addLineToCurrentOrder(
                {
                    product_id: product,
                    price_unit: additional,
                    tax_ids: [["link", ...taxes]],
                },
                {
                    merge: false,
                }
            );
        }
    },
});