/** @odoo-module **/

import { registry } from "@web/core/registry";

const fieldRegistry = registry.category("fields");
const o2m = fieldRegistry.get("one2many");

class PurchaseLineListRendererWithCopy extends o2m.component.components.ListRenderer {

    async onCopyRecord(record) {
        const r = record.data;

        // Step 1: create line (trigger onchange)
        const newRecord = await this.props.list.addNewRecord({
            context: {
                default_product_id: r.product_id?.[0],
            },
        });

        // Step 2: update AFTER onchange
        await newRecord.update({
            product_qty: r.product_qty,
            price_unit: r.price_unit,
            discount: r.discount,
            name: r.name,
            product_uom: r.product_uom,
            date_planned: r.date_planned,
        });

        // Step 3: taxes
        if (r.taxes_id && Array.isArray(r.taxes_id)) {
            await newRecord.update({
                taxes_id: [[6, 0, r.taxes_id]],
            });
        }
    }
}

class PurchaseOrderLineOne2ManyWithCopy extends o2m.component {
    static components = {
        ...o2m.component.components,
        ListRenderer: PurchaseLineListRendererWithCopy,
    };
}

fieldRegistry.add("pol_o2m_copy", {
    ...o2m,
    component: PurchaseOrderLineOne2ManyWithCopy,
});