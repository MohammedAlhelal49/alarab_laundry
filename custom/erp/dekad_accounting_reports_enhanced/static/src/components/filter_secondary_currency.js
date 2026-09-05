/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

/**
 * Patch AccountReportFilters to add secondary currency filter logic.
 *
 * We patch instead of extending a new component so the filter integrates
 * seamlessly into the existing filters panel without any controller changes.
 */
patch(AccountReportFilters.prototype, {

    // ──────────────────────────────────────────────────────────────────────
    // Getter: label shown on the dropdown button
    // ──────────────────────────────────────────────────────────────────────
    get selectedSecondaryCurrencyLabel() {
        const selectedId = this.controller.options.secondary_currency_id;
        if (!selectedId) {
            return _t("In %s", this.controller.options.rounding_unit_names
                ? Object.values(this.controller.options.rounding_unit_names)[1]?.[0] || "Company"
                : "Company");
        }
        const currencies = this.controller.options.secondary_currencies || [];
        const found = currencies.find((c) => c.id === selectedId);
        return found ? _t("In %s", found.name) : _t("Secondary Currency");
    },

    // ──────────────────────────────────────────────────────────────────────
    // Action: select or deselect a secondary currency
    // ──────────────────────────────────────────────────────────────────────
    async filterSecondaryCurrency(currencyId) {
        // Update secondary_currency_id option
        await this.controller.updateOption("secondary_currency_id", currencyId || false);

        // Mark the selected currency in the list (for UI checkmark)
        const currencies = this.controller.options.secondary_currencies || [];
        for (const currency of currencies) {
            currency.selected = currency.id === currencyId;
        }

        // Reload the report with new options — full reload needed since
        // debit/credit/balance values change at SQL level
        await this.applyFilters("secondary_currency_id", 0);
    },

    // ──────────────────────────────────────────────────────────────────────
    // Hide Zero Balance: toggle and reload
    // ──────────────────────────────────────────────────────────────────────
});