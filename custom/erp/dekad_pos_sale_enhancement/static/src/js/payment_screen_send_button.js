/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async afterOrderValidation(...args) {
        const order = this.currentOrder;
        if (!order) return;

        const posConfig = this.pos.config;

        // ✅ Skip if WhatsApp template feature is not enabled in POS config
        if (!posConfig.enable_whatsapp_template) {
            await super.afterOrderValidation(...args);
            return;
        }

        const partner = order.get_partner();
        if (!partner) return;

        const phone = partner.phone || partner.mobile;
        if (!phone) return;

        const phoneDigits = String(phone).replace(/\D/g, "");
        if (!phoneDigits) return;

        const message = order.raw?.whatsapp_message;
        if (!message) {
            await super.afterOrderValidation(...args);
            return;
        }

        const encodedMsg = encodeURIComponent(message);
        const whatsappUrl = `https://web.whatsapp.com/send?phone=${phoneDigits}&text=${encodedMsg}`;

        // ✅ Open WhatsApp Web before any await to avoid popup block
        const popup = window.open(whatsappUrl, "_blank")

        // ⚠️ Notify if browser blocked the pop-up
        if (!popup || popup.closed || typeof popup.closed === "undefined") {
            this.notification.add(
                "Unable to open WhatsApp Web. Please enable pop-ups and third-party redirects in your browser settings.",
                { type: "warning", sticky: true }
            );
        } else {
            this.notification.add("WhatsApp Web opened", { type: "success" });
        }

        await super.afterOrderValidation(...args);
    }
});
