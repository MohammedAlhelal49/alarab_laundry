/** @odoo-module **/

import { registry } from "@web/core/registry";

const fieldRegistry = registry.category("fields");
const solO2M = fieldRegistry.get("sol_o2m");

class SaleOrderLineListRendererWithCopy extends solO2M.component.components.ListRenderer {
    async onCopyRecord(record) {
        const r = record.data;

        const context = {
            default_product_id: r.product_id?.[0],
            default_product_uom_qty: r.product_uom_qty,
            default_price_unit: r.price_unit,
            default_name: r.name,
            default_discount: r.discount,
            default_product_uom: r.product_uom?.[0],
            default_customer_lead: r.customer_lead,
        };

        if (Array.isArray(r.tax_id) && r.tax_id.length) {
            context.default_tax_id = [[6, 0, r.tax_id]];
        }

        await this.props.list.addNewRecord({
            context,
        });
    }
}

class SaleOrderLineOne2ManyWithCopy extends solO2M.component {
    static components = {
        ...solO2M.component.components,
        ListRenderer: SaleOrderLineListRendererWithCopy,
    };
}

fieldRegistry.add("sol_o2m_copy", {
    ...solO2M,
    component: SaleOrderLineOne2ManyWithCopy,
});