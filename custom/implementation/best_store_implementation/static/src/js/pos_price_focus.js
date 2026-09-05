import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        const result = await super.addLineToCurrentOrder(vals, opts, configure);
        console.log("✅ addLineToCurrentOrder patched - setting price mode");
        this.numpadMode = "price";
        return result;
    },

    selectOrderLine(order, line) {
        super.selectOrderLine(order, line);
        console.log("✅ selectOrderLine patched - setting price mode");
        this.numpadMode = "price";
    }
});