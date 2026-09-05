/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    cashierHasPriceControlRights() {
        // Strict mode OFF -> exact normal Odoo behaviour, untouched.
        if (!this.config.use_strict_price_control_list) {
            return super.cashierHasPriceControlRights();
        }

        // Strict mode ON and restrict_price_control ON:
        // ONLY the selected employees can override price.
        // No manager/admin bypass, unlike core.
        const cashier = this.get_cashier();
        if (!cashier) {
            return false;
        }
        const allowedEmployees = this.config.price_control_allowed_employee_ids || [];
        return allowedEmployees.some((employee) => employee.id === cashier.id);
    },
});