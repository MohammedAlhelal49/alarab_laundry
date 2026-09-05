/** @odoo-module **/
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    // Keep your invoice download control
    shouldDownloadInvoice() {
        if (this.pos.config.enable_invoice_pdf_download === false) {
            return false;
        }
        return super.shouldDownloadInvoice();
    },

    async validateOrder(isForceValidate) {
        // Always create an invoice
        this.currentOrder.set_to_invoice(true);

        this.numberBuffer.capture();
        if (!this.check_cash_rounding_has_been_well_applied()) {
            return;
        }

        const linesToRemove = this.currentOrder.lines.filter((line) => {
            const rounding = line.product_id.uom_id.rounding;
            const decimals = Math.max(0, Math.ceil(-Math.log10(rounding)));
            return line.qty.toFixed(decimals) == 0;
        });
        for (const line of linesToRemove) {
            this.currentOrder.removeOrderline(line);
        }

        if (await this._isOrderValid(isForceValidate)) {
            // Remove pending payments before finalizing the validation
            const toRemove = this.paymentLines.filter(
                (line) => !line.is_done() || line.amount === 0
            );
            for (const line of toRemove) {
                this.currentOrder.remove_paymentline(line);
            }

            await this._finalizeValidation();
        }
    },
});
