/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

/**
 * Patch AccountReportFilters to add toggle handlers for all custom options.
 * These are called from the Custom Filters dropdown (custom_filters.xml).
 *
 * Each toggle flips the option and does a full server reload since all
 * options affect SQL-level queries.
 */
patch(AccountReportFilters.prototype, {

    async toggleCustomOption(optionKey) {
        await this.controller.updateOption(
            optionKey,
            !this.controller.options[optionKey],
        );

        // Group by options are mutually exclusive
        if (optionKey === 'group_by_analytic' && this.controller.options.group_by_company) {
            await this.controller.updateOption('group_by_company', false);
        }
        if (optionKey === 'group_by_company' && this.controller.options.group_by_analytic) {
            await this.controller.updateOption('group_by_analytic', false);
        }

        await this.applyFilters(optionKey, 0);
    },
});
