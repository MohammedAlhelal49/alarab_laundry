/** @odoo-module **/

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

console.log("[pos_max_discount_limit] Combined pay() patch loaded");

patch(PosStore.prototype, {
    async pay() {
        console.log("[pos_max_discount_limit] pay() called");

        const order = this.get_order();
        const allowOverride = this.config.allow_price_override;

        if (!order || order.is_empty()) {
            console.warn("[pos_max_discount_limit] Empty order - payment blocked.");
            this.notification.add(_t("No items in order."), { type: "warning" });
            return;
        }

        // ---------------------------------------
        //  Price Validation
        // ---------------------------------------
        const priceViolationLine = order.get_orderlines().find((line) => {
            const product = line.get_product();
            const price = line.get_unit_price();
            const min = product.min_price ?? 0;
            const max = product.max_price ?? 0;
            const hasLimit = min > 0 || max > 0;

            console.log("[POS Price Limit] Checking:", product.display_name || product.name);
            console.log(`[POS Price Limit] Min: ${min}, Max: ${max}, Price: ${price}, Override: ${allowOverride}`);

            return (
                hasLimit &&
                !allowOverride &&
                (price < min || (max > 0 && price > max))
            );
        });

        if (priceViolationLine) {
            const product = priceViolationLine.get_product();
            const price = priceViolationLine.get_unit_price();
            const min = product.min_price ?? 0;
            const max = product.max_price ?? 0;
            const maxText = max > 0 ? max.toFixed(2) : _t("∞");

            await this.dialog.add(AlertDialog, {
                title: _t("Invalid Price"),
                body: _t(
                    "Product: %s\nPrice must be between %s and %s. You entered: %s",
                    product.display_name || product.name,
                    min.toFixed(2),
                    maxText,
                    price.toFixed(2),
                ),
            });
            return;
        }

        // ---------------------------------------
        // Discount Validation
        // ---------------------------------------
        const config = this.config;
        const maxDiscount = config.enable_max_discount_limit
            ? parseFloat(config.max_discount_percent)
            : NaN;

        if (!isNaN(maxDiscount)) {
            const discountViolationLine = order.get_orderlines().find((line) => {
                const discount = parseFloat(line.get_discount());
                const product = line.get_product();
                console.log(`[POS Discount Limit] Checking: ${product.display_name}, Discount: ${discount}`);
                return discount > maxDiscount;
            });

            if (discountViolationLine) {
                const product = discountViolationLine.get_product();
                const discount = parseFloat(discountViolationLine.get_discount());

                console.warn(`[POS Discount Limit] Violation on ${product.display_name}: ${discount}% > ${maxDiscount}%`);

                await this.dialog.add(AlertDialog, {
                    title: _t("Discount Limit Exceeded"),
                    body: _t(
                        "Product: %s\nThe maximum allowed discount is %s%.\nYou entered: %s%.",
                        product.display_name,
                        !isNaN(maxDiscount) ? maxDiscount.toFixed(2) : "?",
                        !isNaN(discount) ? discount.toFixed(2) : "?"
                    ),
                    confirmLabel: _t("OK"),
                });
                return;
            }
        }

        //  All validations passed
        console.log("[pos_max_discount_limit] All validations passed. Proceeding to payment.");
        this.mobile_pane = "right";
        this.env.services.pos.showScreen("PaymentScreen", {
            orderUuid: this.selectedOrderUuid,
        });
    },
});
