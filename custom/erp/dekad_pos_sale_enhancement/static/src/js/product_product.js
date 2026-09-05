/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductProduct } from "@point_of_sale/app/models/product_product";

patch(ProductProduct.prototype, {
    get searchString() {
        const fields = [
            "display_name",
            "default_code",
            "barcode",
            "x_name_en",
            "x_name_ar",
        ];

        return fields
            .map((field) => this[field] || "")
            .filter(Boolean)
            .join(" ")
            .toLowerCase();
    },
});