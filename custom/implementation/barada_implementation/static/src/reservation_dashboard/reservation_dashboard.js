/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";


export class ReservationListController extends ListController {
    setup() {
        super.setup();

        this.orm = useService("orm");

        this.dashboard = useState({
            booked: 0,
            arrived: 0,
            cancelled: 0,
        });

        onWillStart(async () => {
            await this.loadReservationCounts();
        });
    }

    async loadReservationCounts() {
        const model = "crm.reservation";

        // Booked = Scheduled + Delayed
        this.dashboard.booked = await this.orm.searchCount(
            model,
            [
                ["state", "in", ["scheduled", "delayed"]],
            ]
        );

        // Arrived
        this.dashboard.arrived = await this.orm.searchCount(
            model,
            [
                ["state", "=", "arrived"],
            ]
        );

        // Cancelled
        this.dashboard.cancelled = await this.orm.searchCount(
            model,
            [
                ["state", "=", "cancelled"],
            ]
        );
    }

    async filterReservations(state) {
        await this.env.searchModel.clearQuery();

        let domain = [];
        let description = "";

        if (state === "booked") {
            // Booked includes Scheduled + Delayed
            domain = [
                ["state", "in", ["scheduled", "delayed"]],
            ];
            description = "Booked";
        } else if (state === "arrived") {
            domain = [
                ["state", "=", "arrived"],
            ];
            description = "Arrived";
        } else if (state === "cancelled") {
            domain = [
                ["state", "=", "cancelled"],
            ];
            description = "Cancelled";
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


ReservationListController.template =
    "barada_implementation.ReservationListView";


export const reservationListView = {
    ...listView,
    Controller: ReservationListController,
};


registry.category("views").add(
    "reservation_dashboard_list",
    reservationListView
);