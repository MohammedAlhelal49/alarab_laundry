/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListConfirmationDialog } from "@web/views/list/list_confirmation_dialog";

patch(ListConfirmationDialog.prototype, {
    setup() {
        super.setup();

        // only for res.partner
        if (this.props.record?.resModel !== "res.partner") {
            return;
        }

        for (const field of this.props.fields) {
            field.fieldNode.options = {
                ...(field.fieldNode.options || {}),
                no_open: true,
            };
        }
    },
});