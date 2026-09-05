/** © 2025 ehuerta _at_ ixer.mx
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html).
 */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {

    setup() {
        super.setup(...arguments);
    },

    // ===============================
    // UOM Logic
    // ===============================
    set_uom(uom_id) {
        this.uom_rec_id = uom_id;
    },

    set_quantity(quantity, keep_price) {

        if (this.uom_rec_id) {
            this.uom_rec_qty = quantity;
        }

        if (this.uom_rec_id && this.uom_rec_id.uom_type === 'bigger') {
            quantity = quantity * this.uom_rec_id.factor_inv;
        }

        if (this.uom_rec_id && this.uom_rec_id.uom_type === 'smaller') {
            quantity = quantity * this.uom_rec_id.factor;
        }

        return super.set_quantity(quantity, keep_price);
    },

    // ===============================
    // Display Data (Receipt + Orderline)
    // ===============================
    getDisplayData() {

        const data = super.getDisplayData(...arguments);
        const product = this.get_product();

        // ---------- UOM Display ----------
        data.uom_rec_id_name =
            (this.uom_rec_id && this.uom_rec_id !== this.product_uom_id)
                ? ` ${this.uom_rec_qty} ${this.uom_rec_id.name} => `
                : "";

        // ---------- Bilingual Name ----------
        const name_en = product?.name || "";
        const name_ar = product?.x_name_ar || "";

        if (name_ar && name_ar !== name_en) {

            const bilingualName = `${name_en}`;

            /**
             * IMPORTANT:
             * Replace ONLY the base name inside productName
             * instead of overwriting the full string.
             */
            if (data.productName) {
                data.productName = data.productName.replace(name_en, bilingualName);
            }
        }

        return data;
    },
});
