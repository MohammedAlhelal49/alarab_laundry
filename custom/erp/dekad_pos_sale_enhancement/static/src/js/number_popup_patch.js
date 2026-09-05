/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { useBus } from "@web/core/utils/hooks";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";

/**
 * Extend NumberPopup props
 */
NumberPopup.props = {
    ...NumberPopup.props,
    subtotal: {
        type: Number,
        optional: true,
    },
    showAmountInput: {
        type: Boolean,
        optional: true,
    },
};

/**
 * Extend NumberPopup behavior
 * The extra "amount" field only shows/behaves when `showAmountInput` is
 * explicitly passed as true by the caller (Discount / Additional Charge).
 */
patch(NumberPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.discountAmount = 0;

        if (!this.props.showAmountInput) {
            return;
        }

        // Initialize amount from starting percentage
        if (this.props.subtotal && this.state.buffer) {
            const percentage = parseFloat(this.state.buffer || 0);
            this.state.discountAmount = this.roundToTwoDecimals(
                (this.props.subtotal * percentage) / 100
            );
        }

        useBus(this.numberBuffer, "buffer-update", ({ detail }) => {
            if (!this.props.showAmountInput || !this.props.subtotal) {
                return;
            }
            const percentage = parseFloat(detail || 0);
            this.state.discountAmount = this.roundToTwoDecimals(
                (this.props.subtotal * percentage) / 100
            );
        });
    },
    /**
     * Handles direct typing into the percentage input.
     * Replays the typed value through the numpad buffer so the
     * numpad and keyboard stay in sync.
     */
    onPercentInput(ev) {
        const value = ev.target.value;
        this.state.buffer = value;
        if (this.props.showAmountInput && this.props.subtotal) {
            const percentage = parseFloat(value || 0);
            this.state.discountAmount = this.roundToTwoDecimals(
                (this.props.subtotal * percentage) / 100
            );
        }
    },
    /**
     * Handles direct typing into the Amount input.
     */
    onAmountInput(ev) {
        if (!this.props.showAmountInput) {
            return;
        }
        const subtotal = this.props.subtotal || 0;
        if (!subtotal) {
            return; // shouldn't fire anyway since input is disabled, but stay safe
        }
        const amount = this.roundToTwoDecimals(parseFloat(ev.target.value || 0));
        this.state.discountAmount = amount;
        const percentage = (amount / subtotal) * 100;
        this.state.buffer = percentage.toFixed(2);
    },
    /**
     * Rounds a number to at most 2 decimal places, avoiding
     */
    roundToTwoDecimals(value) {
        return Math.round((value + Number.EPSILON) * 100) / 100;
    },
});