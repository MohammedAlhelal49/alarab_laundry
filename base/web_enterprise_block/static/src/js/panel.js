/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ExpiredSubscriptionBlockUI } from "@web_enterprise/enterprise_subscription_service/enterprise_subscription_service";

/*
    Hide Odoo Enterprise expiration blocking overlay
*/

patch(ExpiredSubscriptionBlockUI.prototype, {

    mounted() {
        if (super.mounted) {
            super.mounted();
        }

        setTimeout(() => {

            // Hide blocking overlay
            const overlays = document.querySelectorAll(
                "div[style*='z-index: 1100']"
            );

            overlays.forEach((el) => {
                el.style.display = "none";
            });

            // Hide block ui layer
            const blockers = document.querySelectorAll(".o_blockUI");

            blockers.forEach((el) => {
                el.style.display = "none";
            });

        }, 100);
    },
});
