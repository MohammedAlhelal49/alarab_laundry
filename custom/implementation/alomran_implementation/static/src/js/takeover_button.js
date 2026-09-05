/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class PartnerTakeoverButton extends Component {
    static template = "alomran_implementation.PartnerTakeoverButton";
    static props = {
        ...standardWidgetProps,
        duplicateField: String,
        inactiveField: String,
    };
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    }

    get duplicatePartnerId() {
        const value = this.props.record.data[this.props.duplicateField];
        return value ? value[0] : false;
    }

    get isInactive() {

        return this.props.record.data[this.props.inactiveField];
    }

    onClick() {
        const duplicateId = this.duplicatePartnerId;
        if (!duplicateId) {
            return;
        }

        this.dialog.add(ConfirmationDialog, {
            title: _t("Discard & Take Over Existing Contact"),
            body: _t(
                "This will discard the contact you are creating and reassign the existing contact to you. Continue?"
            ),
            confirm: async () => {
                try {
                    // 1. Do the server-side reassignment FIRST, before touching
                    //    the in-progress record (so nothing here depends on
                    //    the widget/component still being alive afterwards).
                    await this.orm.call(
                        "res.partner",
                        "action_takeover_duplicate_partner",
                        [duplicateId]
                    );

                    // 2. Navigate to the existing contact, forcing a fresh
                    //    controller so it isn't deduped against the current one.
                    await this.action.doAction(
                        {
                            type: "ir.actions.act_window",
                            res_model: "res.partner",
                            res_id: duplicateId,
                            views: [[false, "form"]],
                            target: "current",
                        },
                        { clearBreadcrumbs: true }
                    );

                    // 3. Only now discard the abandoned in-progress record,
                    //    after navigation has already succeeded.
                    if (this.props.record.discard) {
                        await this.props.record.discard();
                    }
                } catch (error) {
                    console.error("Takeover failed:", error);
                    this.notification.add(
                        _t("Something went wrong while taking over the contact. Check the console for details."),
                        { type: "danger" }
                    );
                }
            },
            cancel: () => {},
        });
    }
}

registry.category("view_widgets").add("partner_takeover_button", {
    component: PartnerTakeoverButton,
    extractProps: ({ attrs }) => ({
        duplicateField: attrs.duplicate_field,
        inactiveField: attrs.inactive_field,
    }),
});