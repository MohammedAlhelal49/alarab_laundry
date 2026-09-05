/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NameAndSignature } from "@web/core/signature/name_and_signature";

patch(NameAndSignature.prototype, {
    setup() {
        super.setup?.();

        // Make sure default mode is not auto
        if (this.state.signMode === "auto") {
            this.state.signMode = "draw";
        }

        // Prevent switching to auto
        this.blockAutoSignature = true;
    },

    onClickSignAuto() {
        // Block the Auto mode entirely
        if (this.blockAutoSignature) {
            return;
        }
        this.setMode("auto");
    },

    drawCurrentName() {
        if (this.blockAutoSignature) {
            return;
        }
        return super.drawCurrentName?.();
    },

    getSVGTextFont(font) {
        if (this.blockAutoSignature) {
            return "";
        }
        return super.getSVGTextFont?.(font);
    },
});