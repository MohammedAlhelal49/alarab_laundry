/** @odoo-module **/

import { registry } from "@web/core/registry";

const fieldRegistry = registry.category("fields");
const amlO2M = fieldRegistry.get("one2many");

function formatDate(value) {
    if (!value) return value;

    if (typeof value === "string") return value;

    if (value instanceof Date) {
        return value.toISOString().split("T")[0];
    }

    if (value.toISO) {
        return value.toISODate();
    }

    return value;
}

class AccountMoveLineListRendererWithCopy extends amlO2M.component.components.ListRenderer {

    async onCopyRecord(record) {
        const r = record.data;

        const context = {
            default_product_id: r.product_id?.[0],
            default_quantity: r.quantity,
            default_price_unit: r.price_unit,
            default_name: r.name,
            default_discount: r.discount,
        };

        // partner
        if (r.partner_id) {
            context.default_partner_id = r.partner_id[0];
        }

        // taxes
        if (r.tax_ids && Array.isArray(r.tax_ids)) {
            context.default_tax_ids = [[6, 0, r.tax_ids]];
        }

        // account
        if (r.account_id) {
            context.default_account_id = r.account_id[0];
        }

        // analytic
        if (r.analytic_account_id) {
            context.default_analytic_account_id = r.analytic_account_id[0];
        }

        if (r.analytic_distribution) {
            context.default_analytic_distribution = r.analytic_distribution;
        }

        // maturity date
        if (r.date_maturity) {
            context.default_date_maturity = formatDate(r.date_maturity);
        }

        // discount date
        if (r.discount_date) {
            context.default_discount_date = formatDate(r.discount_date);
        }

        // tax tag invert
        if (r.tax_tag_invert !== undefined) {
            context.default_tax_tag_invert = r.tax_tag_invert;
        }

        // discount amount currency
        if (r.discount_amount_currency) {
            context.default_discount_amount_currency = r.discount_amount_currency;
        }



        await this.props.list.addNewRecord({
            context: context,
        });
    }
}

class AccountMoveLineOne2ManyWithCopy extends amlO2M.component {
    static components = {
        ...amlO2M.component.components,
        ListRenderer: AccountMoveLineListRendererWithCopy,
    };
}

fieldRegistry.add("aml_o2m_copy", {
    ...amlO2M,
    component: AccountMoveLineOne2ManyWithCopy,
});