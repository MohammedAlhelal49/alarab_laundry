/** @odoo-module **/

console.log("[HRMS Dashboard] module loaded");

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { onMounted, Component, useRef } from "@odoo/owl";
import { onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { patch } from "@web/core/utils/patch";

// Palette shared by every chart in this dashboard.
const CHART_COLORS = [
    "#70cac1", "#659d4e", "#208cc2", "#4d6cb1", "#584999",
    "#8e559e", "#cf3650", "#f65337", "#fe7139", "#ffa433",
    "#ffc25b", "#f8e54b", "#ff6384", "#4bc0c0", "#ffcd56",
    "#c9cbcf", "#36a2eb",
];

export class HrDashboard extends Component {

    static template = "HrDashboardMain";
    static props = ["*"];

    setup() {
        this.effect = useService("effect");
        this.action = useService("action");
        this.orm = useService("orm");

        this.log_in_out = useRef("log_in_out");
        this.emp_graph = useRef("emp_graph");
        this.leave_graph = useRef("leave_graph");
        this.join_resign_trend = useRef("join_resign_trend");
        this.attrition_rate = useRef("attrition_rate");

        this.state = useState({
            is_manager: false,
            date_range: "week",
            dashboards_templates: [
                "LoginEmployeeDetails",
                "ManagerDashboard",
                "EmployeeDashboard",
            ],
            employee_birthday: [],
            // upcoming_events: [],
            announcements: [],
            login_employee: null,
            templates: [],
            user_hase_employee: 0,
        });

        // =====================================================
        // LOAD DASHBOARD DATA
        // =====================================================
        onWillStart(async () => {
            this.state.user_hase_employee = await this.orm.call(
                "hr.employee", "check_user_has_employee", []
            );

            this.isHrManager = await user.hasGroup("hr.group_hr_manager");

            this.state.login_employee = null;

            if (!this.state.user_hase_employee) {
                this.state.is_manager = false;
                return;
            }

            const isManager = await this.orm.call(
                "hr.employee", "check_user_group", []
            );
            this.state.is_manager = Boolean(isManager);

            const empDetails = await this.orm.call(
                "hr.employee", "get_user_employee_details", []
            );
            if (empDetails && empDetails.length) {
                this.state.login_employee = empDetails[0];
            }

            const res = await this.orm.call("hr.employee", "get_upcoming", []);
            if (res) {
                this.state.employee_birthday = res["birthday"] || [];
                // this.state.upcoming_events = res["event"] || [];
                this.state.announcements = res["announcement"] || [];
            }
        });

        // =====================================================
        // AFTER DASHBOARD IS IN DOM
        // =====================================================
        onMounted(() => {
            this.title = "Dashboard";

            if (!this.state.user_hase_employee || !this.state.login_employee?.id) {
                console.log("[HRMS Dashboard] no employee linked, skipping charts");
                return;
            }

            if (typeof Chart === "undefined") {
                // Should never happen now that Chart.js loads before this
                // module in the manifest, but guard against it explicitly
                // instead of throwing and silently killing every chart.
                console.error(
                    "[HRMS Dashboard] Chart.js is not loaded! " +
                    "Check the asset load order in __manifest__.py " +
                    "(Chart.js CDN entry must come before dashboard.js)."
                );
                return;
            }

            console.log("[HRMS Dashboard] Chart.js version:", Chart.version);
            this.render_graphs();
        });
    }

    // =========================================================
    // GRAPH CONTROLLER
    // =========================================================
    render_graphs() {
        if (!this.state.user_hase_employee || !this.state.login_employee?.id) {
            return;
        }

        // Personal employee charts
        this.render_employee_skill();
        this.render_leave_graph();

        // Manager-only charts
        if (this.state.is_manager) {
            this.render_department_employee();
            this.update_join_resign_trends();
            this.update_monthly_attrition();
        }
    }

    // =========================================================
    // DEPARTMENT EMPLOYEE PIE CHART (Chart.js 2.9.4 syntax)
    // MANAGER ONLY
    // =========================================================
    async render_department_employee() {
        try {
            console.log("[HRMS Dashboard] render_department_employee: start");

            const canvas = document.getElementById("employeePieChart");
            if (!canvas) {
                console.warn("[HRMS Dashboard] employeePieChart canvas not found");
                return;
            }

            const data = await this.orm.call("hr.employee", "get_dept_employee", []);
            console.log("[HRMS Dashboard] department data:", data);

            if (!canvas.isConnected || !data || !data.length) {
                console.warn("[HRMS Dashboard] no department data to render");
                return;
            }

            const labels = data.map((item) => item.label);
            const values = data.map((item) => Number(item.value || 0));
            const chartColors = data.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]);

            console.log("[HRMS Dashboard] pie labels:", labels);
            console.log("[HRMS Dashboard] pie values:", values);
            console.log("[HRMS Dashboard] pie colors:", chartColors);

            const ctx = canvas.getContext("2d");
            if (!ctx) {
                console.warn("[HRMS Dashboard] could not get 2d context for pie chart");
                return;
            }

            if (this.departmentEmployeeChart) {
                this.departmentEmployeeChart.destroy();
            }

            // Chart.js 2.9.4 syntax: legend/tooltips are TOP-LEVEL options,
            // not nested under `plugins` (that's a v3/v4-only structure).
            this.departmentEmployeeChart = new Chart(ctx, {
                type: "pie",
                data: {
                    labels: labels,
                    datasets: [{
                        label: "Employees",
                        data: values,
                        backgroundColor: chartColors,
                        hoverBackgroundColor: chartColors,
                        borderColor: "#ffffff",
                        borderWidth: 2,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    legend: {
                        display: true,
                        position: "right",
                        labels: {
                            fontColor: "#000000",
                            usePointStyle: true,
                        },
                    },
                    tooltips: {
                        callbacks: {
                            label: function (tooltipItem, chartData) {
                                const index = tooltipItem.index;
                                const label = chartData.labels[index] || "";
                                const value = Number(chartData.datasets[0].data[index] || 0);
                                const total = chartData.datasets[0].data.reduce(
                                    (sum, n) => sum + Number(n || 0), 0
                                );
                                const pct = total ? ((value / total) * 100).toFixed(2) : "0.00";
                                return `${label}: ${value} (${pct}%)`;
                            },
                        },
                    },
                },
            });

            console.log(
                "[HRMS Dashboard] pie chart created, backgroundColor =",
                this.departmentEmployeeChart.data.datasets[0].backgroundColor
            );
        } catch (err) {
            console.error("[HRMS Dashboard] render_department_employee failed:", err);
        }
    }


    // =========================================================
    // MONTHLY LEAVE BAR CHART
    // MANAGER ONLY
    // =========================================================

    async render_leave_graph() {
        try {
            const canvas = document.getElementById("leave_barChart");

            if (!canvas) {
                return;
            }

            const data = await this.orm.call(
                "hr.employee",
                "get_employee_monthly_leave",
                []
            );

            console.log(
                "[HRMS Dashboard] employee monthly leave:",
                data
            );

            if (!canvas.isConnected || !Array.isArray(data)) {
                return;
            }

            const labels = data.map((item) => item.month);
            const values = data.map((item) => Number(item.days || 0));

            const ctx = canvas.getContext("2d");

            if (!ctx) {
                return;
            }

            if (this.leaveBarChart) {
                this.leaveBarChart.destroy();
                this.leaveBarChart = null;
            }

            this.leaveBarChart = new Chart(ctx, {
                type: "bar",

                data: {
                    labels: labels,

                    datasets: [{
                        label: "My Leave Days",
                        data: values,

                        backgroundColor: "#ff618a",
                        borderColor: "#ff4d7d",
                        borderWidth: 1,

                        hoverBackgroundColor: "#ff4775",
                        hoverBorderColor: "#ff2f64",
                    }],
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,

                    legend: {
                        display: true,
                        position: "top",

                        labels: {
                            fontColor: "#333333",
                        },
                    },

                    tooltips: {
                        callbacks: {
                            label: function (tooltipItem) {
                                const value = Number(
                                    tooltipItem.yLabel || 0
                                );

                                return value + (
                                    value === 1
                                        ? " leave day"
                                        : " leave days"
                                );
                            },
                        },
                    },

                    scales: {
                        xAxes: [{
                            gridLines: {
                                display: false,
                            },

                            ticks: {
                                fontColor: "#666666",
                            },
                        }],

                        yAxes: [{
                            ticks: {
                                beginAtZero: true,
                                fontColor: "#666666",
                            },

                            scaleLabel: {
                                display: true,
                                labelString: "Leave Days",
                            },
                        }],
                    },
                },
            });

        } catch (err) {
            console.error(
                "[HRMS Dashboard] render_leave_graph failed:",
                err
            );
        }
    }

    // =========================================================
    // JOIN / RESIGN TREND (line chart) - Chart.js 2.9.4
    // MANAGER ONLY
    // =========================================================
    async update_join_resign_trends() {
        try {
            const canvas = document.getElementById("lineChart");
            if (!canvas) {
                // Section is commented out in the XML by default; skip quietly.
                return;
            }

            const data = await this.orm.call("hr.employee", "join_resign_trends", []);
            if (!canvas.isConnected || !data || !data.length || !data[0]?.values) {
                return;
            }

            const labels = data[0].values.map((d) => d.l_month);
            const datasets = data.map((dataset, index) => ({
                label: dataset.name,
                data: dataset.values.map((d) => d.count),
                borderColor: CHART_COLORS[index % CHART_COLORS.length],
                fill: false,
                tension: 0.1,
                borderWidth: 2,
            }));

            const ctx = canvas.getContext("2d");
            if (!ctx) {
                return;
            }

            if (this.joinResignChart) {
                this.joinResignChart.destroy();
            }

            this.joinResignChart = new Chart(ctx, {
                type: "line",
                data: { labels: labels, datasets: datasets },
                options: {
                    responsive: false,
                    maintainAspectRatio: false,
                    legend: {
                        display: true,
                        labels: { fontColor: "#000000" },
                    },
                    scales: {
                        xAxes: [{ scaleLabel: { display: true, labelString: "Month" } }],
                        yAxes: [{ ticks: { beginAtZero: true }, scaleLabel: { display: true, labelString: "Count" } }],
                    },
                },
            });

            console.log("[HRMS Dashboard] join/resign chart created");
        } catch (err) {
            console.error("[HRMS Dashboard] update_join_resign_trends failed:", err);
        }
    }

    // =========================================================
    // MONTHLY ATTRITION (line chart) - Chart.js 2.9.4
    // MANAGER ONLY
    // =========================================================
    async update_monthly_attrition() {
        try {
            const canvas = document.getElementById("attritionRateChart");
            if (!canvas) {
                // Section is commented out in the XML by default; skip quietly.
                return;
            }

            const data = await this.orm.call("hr.employee", "get_attrition_rate", []);
            if (!canvas.isConnected || !data) {
                return;
            }

            const labels = data.map((d) => d.month);
            const attritionData = data.map((d) => d.attrition_rate);

            const ctx = canvas.getContext("2d");
            if (!ctx) {
                return;
            }

            if (this.attritionChart) {
                this.attritionChart.destroy();
            }

            this.attritionChart = new Chart(ctx, {
                type: "line",
                data: {
                    labels: labels,
                    datasets: [{
                        label: "Attrition Rate",
                        data: attritionData,
                        backgroundColor: CHART_COLORS[0],
                        borderColor: CHART_COLORS[0],
                        fill: false,
                        tension: 0.1,
                        pointRadius: 3,
                        pointHoverRadius: 6,
                    }],
                },
                options: {
                    responsive: false,
                    maintainAspectRatio: false,
                    tooltips: {
                        callbacks: {
                            label: (tooltipItem) => `Attrition Rate: ${tooltipItem.yLabel}`,
                        },
                    },
                    legend: {
                        display: true,
                        position: "top",
                        labels: { fontColor: "#000000" },
                    },
                    scales: {
                        xAxes: [{ scaleLabel: { display: true, labelString: "Month" } }],
                        yAxes: [{ ticks: { beginAtZero: true }, scaleLabel: { display: true, labelString: "Attrition Rate" } }],
                    },
                },
            });

            console.log("[HRMS Dashboard] attrition chart created");
        } catch (err) {
            console.error("[HRMS Dashboard] update_monthly_attrition failed:", err);
        }
    }

    // =========================================================
    // EMPLOYEE SKILL CHART (polar area) - Chart.js 2.9.4
    // =========================================================
    async render_employee_skill() {
        try {
            const canvas = document.getElementById("skillChart");
            if (!canvas) {
                console.warn("[HRMS Dashboard] skillChart canvas not found");
                return;
            }

            const data = await this.orm.call("hr.employee", "get_employee_skill", []);
            if (!canvas.isConnected || !data) {
                return;
            }

            const labels = data.map((d) => d.skills);
            const skillData = data.map((d) => d.progress);

            const ctx = canvas.getContext("2d");
            if (!ctx) {
                return;
            }

            if (this.skillChart) {
                this.skillChart.destroy();
            }

            this.skillChart = new Chart(ctx, {
                type: "polarArea",
                data: {
                    labels: labels,
                    datasets: [{
                        label: "Skill",
                        data: skillData,
                        backgroundColor: CHART_COLORS,
                        borderColor: "#ffffff",
                        borderWidth: 2,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    tooltips: {
                        callbacks: {
                            label: (tooltipItem, chartData) => {
                                const value = chartData.datasets[0].data[tooltipItem.index];
                                return `Skill: ${value}`;
                            },
                        },
                    },
                    legend: {
                        display: true,
                        position: "right",
                        labels: { fontColor: "#000000" },
                    },
                    scale: {
                        ticks: { beginAtZero: true, stepSize: 1,display: false, },
                    },
                },
            });

            console.log("[HRMS Dashboard] skill chart created");
        } catch (err) {
            console.error("[HRMS Dashboard] render_employee_skill failed:", err);
        }
    }

    // =========================================================
    // EVENT METHODS
    // =========================================================
    add_attendance() {
        this.action.doAction({
            name: _t("Attendances"),
            type: "ir.actions.act_window",
            res_model: "hr.attendance",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        });
    }

    add_leave() {
        this.action.doAction({
            name: _t("Leave Request"),
            type: "ir.actions.act_window",
            res_model: "hr.leave",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        });
    }

    add_expense() {
        this.action.doAction({
            name: _t("Expense"),
            type: "ir.actions.act_window",
            res_model: "hr.expense",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        });
    }

    leaves_to_approve() {
        this.action.doAction({
            name: _t("Leave Request"),
            type: "ir.actions.act_window",
            res_model: "hr.leave",
            view_mode: "tree,form,calendar",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "in", ["confirm", "validate1"]]],
            target: "current",
        });
    }

    leave_allocations_to_approve() {
        this.action.doAction({
            name: _t("Leave Allocation Request"),
            type: "ir.actions.act_window",
            res_model: "hr.leave.allocation",
            view_mode: "tree,form,calendar",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "in", ["confirm", "validate1"]]],
            target: "current",
        });
    }

    job_applications_to_approve() {
        this.action.doAction({
            name: _t("Applications"),
            type: "ir.actions.act_window",
            res_model: "hr.applicant",
            view_mode: "tree,kanban,form,pivot,graph,calendar",
            views: [
                [false, "list"], [false, "kanban"], [false, "form"],
                [false, "pivot"], [false, "graph"], [false, "calendar"],
            ],
            context: {},
            target: "current",
        });
    }

    leaves_request_today() {
        const date = new Date();
        this.action.doAction({
            name: _t("Leaves Today"),
            type: "ir.actions.act_window",
            res_model: "hr.leave",
            view_mode: "tree,form,calendar",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["date_from", "<=", date],
                ["date_to", ">=", date],
                ["state", "=", "validate"],
            ],
            target: "current",
        });
    }

    leaves_request_month() {
        const date = new Date();
        const firstDay = new Date(date.getFullYear(), date.getMonth(), 1);
        const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
        const fday = firstDay.toJSON().slice(0, 10);
        const lday = lastDay.toJSON().slice(0, 10);

        this.action.doAction({
            name: _t("This Month Leaves"),
            type: "ir.actions.act_window",
            res_model: "hr.leave",
            view_mode: "tree,form,calendar",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["date_from", ">", fday],
                ["state", "=", "validate"],
                ["date_from", "<", lday],
            ],
            target: "current",
        });
    }

    hr_payslip() {
        if (!this.state.login_employee?.id) {
            return;
        }
        this.action.doAction({
            name: _t("Employee Payslips"),
            type: "ir.actions.act_window",
            res_model: "hr.payslip",
            view_mode: "tree,form,calendar",
            views: [[false, "list"], [false, "form"]],
            domain: [["employee_id", "=", this.state.login_employee.id]],
            target: "current",
        });
    }

    async hr_contract() {
        if (this.isHrManager) {
            this.action.doAction({
                name: _t("Contracts"),
                type: "ir.actions.act_window",
                res_model: "hr.contract",
                view_mode: "list,form",
                views: [[false, "list"], [false, "form"]],
                domain: [["employee_id", "=", this.state.login_employee.id]],
                context: {},
                target: "current",
            });
        }
    }

    hr_timesheets() {
        if (!this.state.login_employee?.id) {
            return;
        }
        this.action.doAction({
            name: _t("Timesheets"),
            type: "ir.actions.act_window",
            res_model: "account.analytic.line",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            context: { search_default_month: true },
            domain: [["employee_id", "=", this.state.login_employee.id]],
            target: "current",
        });
    }

    employee_total_leaves() {
        if (!this.state.login_employee?.id) {
            return;
        }

        this.action.doAction({
            name: _t("My Approved Leaves"),
            type: "ir.actions.act_window",
            res_model: "hr.leave",
            view_mode: "list,form,calendar",
            views: [
                [false, "list"],
                [false, "form"],
                [false, "calendar"],
            ],
            domain: [
                ["state", "=", "validate"],
                ["employee_id", "=", this.state.login_employee.id],
            ],
            target: "current",
        });
    }

    async refreshAttendanceData() {
        const empDetails = await this.orm.call(
            "hr.employee",
            "get_user_employee_details",
            []
        );

        if (empDetails && empDetails.length) {
            const freshEmployee = empDetails[0];

            this.state.login_employee.attendance_lines =
                freshEmployee.attendance_lines || [];

            this.state.login_employee.attendance_state =
                freshEmployee.attendance_state;
        }
    }

    // =========================================================
    // ATTENDANCE BUTTON
    // =========================================================
    attendance_sign_in_out() {
        if (!this.state.login_employee?.id) {
            return;
        }

        this.update_attendance();
    }

    async update_attendance() {
        const self = this;

        if (!this.state.login_employee?.id) {
            this.effect.add({
                message: _t("No employee is linked to your user in the current company."),
                type: "danger",
                fadeout: "fast",
            });
            return;
        }

        if (!navigator.geolocation) {
            this.effect.add({
                message: _t("Geolocation is not supported by this browser."),
                type: "danger",
                fadeout: "fast",
            });
            return;
        }

        navigator.geolocation.getCurrentPosition(
            async function (position) {
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;

                try {
                    const result = await self.orm.call(
                        "hr.employee",
                        "attendance_manual",
                        [latitude, longitude]
                    );

                    if (result) {

                        // Reload attendance from the server immediately
                        await self.refreshAttendanceData();

                        const attendanceState =
                            self.state.login_employee.attendance_state;

                        const message =
                            attendanceState === "checked_in"
                                ? "Checked In"
                                : "Checked Out";

                        self.effect.add({
                            message: _t("Successfully " + message),
                            type: "rainbow_man",
                            fadeout: "fast",
                        });
                    }
                } catch (error) {
                    console.error("[HRMS Dashboard] Attendance error:", error);

                    self.effect.add({
                        message: _t("Unable to update attendance."),
                        type: "danger",
                        fadeout: "fast",
                    });
                }
            },
            function () {
                self.effect.add({
                    message: _t(
                        "Unable to retrieve your location. Make sure you allowed location access."
                    ),
                    type: "danger",
                    fadeout: "fast",
                });
            }
        );
    }
}

registry.category("actions").add("hr_dashboard", HrDashboard);

patch(ActivityMenu.prototype, {
    setup() {
        super.setup();
        const self = this;

        onMounted(() => {
            this.env.bus.addEventListener("signin_signout", ({ detail }) => {
                if (detail.mode === "checked_in") {
                    self.state.checkedIn = detail.mode;
                } else {
                    self.state.checkedIn = false;
                }
            });
        });
    },
});