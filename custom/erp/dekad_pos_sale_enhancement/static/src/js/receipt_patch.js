/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

console.log("[pos_customer_name_receipt] Patch file loaded");

patch(PosStore.prototype, {
    orderExportForPrinting(order) {
        const result = super.orderExportForPrinting(order);
        const partner = order?.get_partner();
        const partnerName = partner?.name || '';

        result.partner_name = partnerName;
        console.log("[pos_customer_name_receipt] Injected partner_name into receipt data:", partnerName);

        return result;
    }
});
