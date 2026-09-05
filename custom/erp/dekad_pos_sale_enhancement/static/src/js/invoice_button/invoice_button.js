/** @odoo-module **/
import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { patch } from "@web/core/utils/patch";
patch(InvoiceButton.prototype, {
 async _downloadInvoice(orderId) {
                try {
            const orderWithInvoice = await this.pos.data.read("pos.order", [orderId], [], {
                load: false,
            });
            const order = orderWithInvoice[0];
            const accountMoveId = order.raw.account_move;
            if (accountMoveId) {
               window.open(`/report/pdf/account.report_invoice_with_payments/${accountMoveId}`, '_blank');
            }
        } catch (error) {
            if (error instanceof Error) {
                throw error;
            } else {
                // NOTE: error here is most probably undefined
                this.dialog.add(AlertDialog, {
                    title: _t("Network Error"),
                    body: _t("Unable to download invoice."),
                });
            }
        }

    }
});