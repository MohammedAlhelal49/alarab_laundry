/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const data = super.getReceiptHeaderData(...arguments);
        const partner = order.get_partner();
        const invoiceNumber = order.raw?.invoice_number;


        const now = new Date();
        const current_datetime = now.toLocaleString();


        console.log("Invoice Number (account.move.name):", invoiceNumber);

        return {
            ...data,
            partner: partner ? {
                name: partner.name,
                street: partner.street,
            //     city: partner.city,
            //     zip: partner.zip,
                state: partner.state_id?.[1],
                country: partner.country_id?.[1],
                phone: partner.phone,
                mobile: partner.mobile,
                email: partner.email,
            } : null,
            invoice_number: invoiceNumber || null,
            current_datetime : current_datetime || null
        };
    },
});
