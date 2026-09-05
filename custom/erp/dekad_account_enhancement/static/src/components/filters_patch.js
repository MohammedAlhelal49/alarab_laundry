/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

// Make the Options dropdown visible on reports that have show_company_column
patch(AccountReportFilters.prototype, {
    get hasExtraOptionsFilter() {
        return super.hasExtraOptionsFilter || "show_company_column" in this.controller.options;
    },
});