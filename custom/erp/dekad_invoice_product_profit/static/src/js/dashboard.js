/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
export class ProfitLossDashboard extends Component {
    static template = "dekad_invoice_product_profit.Dashboard";
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            date_from: false,
            date_to: false,
            summary: {},
            invoice_lines: [],
            expense_lines: [],
            // Pagination state for the Invoice Profit Report table
            currentPage: 1,
            pageSize: 10,
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }
    formatAmount(value) {
        return value ? value.toFixed(2) : '0.00';
    }
    async loadData() {
        const summary = await this.orm.call(
            "dekad.profit.loss.dashboard", "get_summary",
            [this.state.date_from, this.state.date_to]
        );
        const invoiceData = await this.orm.call(
            "dekad.profit.loss.dashboard", "get_invoice_profit_report",
            [this.state.date_from, this.state.date_to]
        );
        const expenseData = await this.orm.call(
            "dekad.profit.loss.dashboard", "get_expense_report",
            [this.state.date_from, this.state.date_to]
        );
        this.state.summary = summary;
        this.state.invoice_lines = invoiceData.invoice_lines;
        this.state.expense_lines = expenseData.expense_lines;

        this.state.currentPage = 1;
    }
    // ---- Pagination helpers for Invoice Profit Report ----
    get totalPages() {
        return Math.max(
            1, Math.ceil(this.state.invoice_lines.length / this.state.pageSize)
        );
    }
    get paginatedInvoiceLines() {
        const start = (this.state.currentPage - 1) * this.state.pageSize;
        const end = start + this.state.pageSize;
        return this.state.invoice_lines.slice(start, end);
    }
    get pageNumbers() {
        // e.g. totalPages = 4 -> [1, 2, 3, 4]
        return Array.from({ length: this.totalPages }, (_, i) => i + 1);
    }
    goToPage(page) {
        if (page < 1 || page > this.totalPages) {
            return;
        }
        this.state.currentPage = page;
    }
    previousPage() {
        this.goToPage(this.state.currentPage - 1);
    }
    nextPage() {
        this.goToPage(this.state.currentPage + 1);
    }
    async onDateFromChange(ev) {
                this.state.date_from = ev.target.value;
                await this.loadData();
    }
    async onDateToChange(ev) {
         this.state.date_to = ev.target.value;
         await this.loadData();
    }
}
registry.category("actions").add("dekad_invoice_product_profit_dashboard_action", ProfitLossDashboard);
