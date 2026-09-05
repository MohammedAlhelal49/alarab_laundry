import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

// Patch 1: إضافة بيانات الزبون على الإيصال
patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(baseUrl, headerData);
        const partner = this.get_partner();
        result.partner_name = partner?.name || "";
        result.partner_mobile = partner?.mobile || partner?.phone || "";
        return result;
    },
});

// Patch 2: تغيير الـ template
OrderReceipt.template = "london_laundry_implementation.OrderReceipt";
