import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        console.log(this.is_paid())
        if(this.config.default_partner_id && !this.partner_id && !this.uiState.locked){
            this.update({ partner_id: this.config.default_partner_id });
        }
    },
});
