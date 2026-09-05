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
     * Date domains used by dashboard.
     *
     * Expired:
     *      remaining_days <= 0
     *      expiry_date <= today
     *
     * Near expiration:
     *      remaining_days 1 -> 15
     */
    getDateDomains() {
        const today = new Date();

        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);

        const fifteenDaysLater = new Date(today);
        fifteenDaysLater.setDate(
            fifteenDaysLater.getDate() + 15
        );

        const todayStr = this.formatDate(today);
        const tomorrowStr = this.formatDate(tomorrow);
        const fifteenDaysLaterStr =
            this.formatDate(fifteenDaysLater);

        return {
            expired: [
                ["expiry_date", "!=", false],
                ["expiry_date", "<=", todayStr],
            ],

            nearExpiration: [
                ["expiry_date", ">=", tomorrowStr],
                ["expiry_date", "<=", fifteenDaysLaterStr],
            ],
        };
    }

    /**
     * Get the domain of the action that opened this list.
     *
     * Example when opened from employee:
     *
     * [
     *     ["employee_ref_id", "=", 123]
     * ]
     *
     * When opened from Documents menu it will normally be [].
     */
    getBaseDomain() {
        return this.props.domain || [];
    }

    /**
     * Load dashboard counts.
     *
     * IMPORTANT:
     * Every count includes the action/list base domain.
     */
    async loadDocumentCounts() {
        const model = "hr.employee.document";

        const baseDomain = this.getBaseDomain();
        const domains = this.getDateDomains();

        // -----------------------------------------------------
        // Total Documents
        // -----------------------------------------------------
        this.dashboard.total = await this.orm.searchCount(
            model,
            baseDomain
        );

        // -----------------------------------------------------
        // Near Expiration
        // -----------------------------------------------------
        this.dashboard.nearExpiration =
            await this.orm.searchCount(
                model,
                [
                    ...baseDomain,
                    ...domains.nearExpiration,
                ]
            );

        // -----------------------------------------------------
        // Expired
        // -----------------------------------------------------
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

        // Documents = remove dashboard filter.
        // The action/base domain remains active.
        if (type === "all") {
            return;
        }

        const domains = this.getDateDomains();

        let domain = [];
        let description = "";

        if (type === "near_expiration") {
            domain = domains.nearExpiration;
            description = "Near Expiration";
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