/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";


export class EmployeeDocumentListController extends ListController {
    setup() {
        super.setup();

        this.orm = useService("orm");

        this.dashboard = useState({
            total: 0,
            nearExpiration: 0,
            expired: 0,

            // Default = 15 days
            nearExpirationDays: 15,
        });

        onWillStart(async () => {
            await this.loadDocumentCounts();
        });
    }

    /**
     * Convert JS Date to YYYY-MM-DD.
     */
    formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");

        return `${year}-${month}-${day}`;
    }

    /**
     * Label displayed inside Near Expiration card.
     */
    get nearExpirationLabel() {
        const days = this.dashboard.nearExpirationDays;

        if (days === 30) {
            return "Within 1 Month";
        }
        if (days === 90) {
            return "Within 3 Months";
        }
        if (days === 180) {
            return "Within 6 Months";
        }

        return "Within 15 Days";
    }

    /**
     * Dashboard date domains.
     */
    getDateDomains() {
        const today = new Date();

        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);

        const expirationLimit = new Date(today);
        expirationLimit.setDate(
            expirationLimit.getDate() +
            this.dashboard.nearExpirationDays
        );

        const todayStr = this.formatDate(today);
        const tomorrowStr = this.formatDate(tomorrow);
        const expirationLimitStr = this.formatDate(expirationLimit);

        return {
            expired: [
                ["expiry_date", "!=", false],
                ["expiry_date", "<=", todayStr],
            ],

            nearExpiration: [
                ["expiry_date", ">=", tomorrowStr],
                ["expiry_date", "<=", expirationLimitStr],
            ],
        };
    }

    /**
     * Get action/list base domain.
     */
    getBaseDomain() {
        return this.props.domain || [];
    }

    async setNearExpirationDays(days, ev) {
        if (ev) {
            ev.stopPropagation();
        }

        // Change selected period immediately
        this.dashboard.nearExpirationDays = days;

        // Reload KPI count for the selected period
        await this.loadNearExpirationCount();

        // Apply the selected period to the list as well
        await this.filterDocuments("near_expiration");
    }


    async loadNearExpirationCount() {
        const model = "hr.employee.document";

        const baseDomain = this.getBaseDomain();
        const domains = this.getDateDomains();

        // Remember which period this RPC belongs to.
        const requestedDays = this.dashboard.nearExpirationDays;

        const count = await this.orm.searchCount(
            model,
            [
                ...baseDomain,
                ...domains.nearExpiration,
            ]
        );

        // Do not let an old RPC overwrite a newer selection.
        if (requestedDays === this.dashboard.nearExpirationDays) {
            this.dashboard.nearExpiration = count;
        }
    }

    /**
     * Load dashboard counts.
     */
    async loadDocumentCounts() {
        const model = "hr.employee.document";

        const baseDomain = this.getBaseDomain();
        const domains = this.getDateDomains();

        // Total
        this.dashboard.total = await this.orm.searchCount(
            model,
            baseDomain
        );

        // Near Expiration
        this.dashboard.nearExpiration =
            await this.orm.searchCount(
                model,
                [
                    ...baseDomain,
                    ...domains.nearExpiration,
                ]
            );

        // Expired
        this.dashboard.expired =
            await this.orm.searchCount(
                model,
                [
                    ...baseDomain,
                    ...domains.expired,
                ]
            );
    }

    /**
     * Filter records when dashboard card is clicked.
     */
    async filterDocuments(type) {
        await this.env.searchModel.clearQuery();

        if (type === "all") {
            return;
        }

        const domains = this.getDateDomains();

        let domain = [];
        let description = "";

        if (type === "near_expiration") {
            domain = domains.nearExpiration;
            description = this.nearExpirationLabel;
        } else if (type === "expired") {
            domain = domains.expired;
            description = "Expired";
        }

        this.env.searchModel.createNewFilters([
            {
                description: description,
                domain: domain,
                type: "filter",
            },
        ]);
    }
}


EmployeeDocumentListController.template =
    "oh_employee_documents_expiry.EmployeeDocumentListView";


export const employeeDocumentListView = {
    ...listView,
    Controller: EmployeeDocumentListController,
};


registry.category("views").add(
    "employee_document_dashboard_list",
    employeeDocumentListView
);