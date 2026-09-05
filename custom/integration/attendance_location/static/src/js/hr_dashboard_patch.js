/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { HrDashboard } from '@hrms_dashboard/js/dashboard';

// Safe wrapper to avoid null errors on missing canvas elements
function safeGetContext(id) {
    const el = document.getElementById(id);
    return el ? el.getContext('2d') : null;
}

patch(HrDashboard.prototype, {

    async render_department_employee() {
        const ctx = safeGetContext('employeePieChart');
        if (!ctx) return;

        const colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139', '#ffa433', '#ffc25b', '#f8e54b'];
        const data = await this.orm.call('hr.employee', 'get_dept_employee', []);
        if (!data) return;

        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    data: data.map(d => d.value),
                    backgroundColor: colors,
                }]
            },
            options: { responsive: true }
        });
    },

    async render_leave_graph() {
        const barCtx = safeGetContext('leave_barChart');
        const pieCtx = safeGetContext('leave_doughnutChart');
        if (!barCtx || !pieCtx) return;

        const colors = ['#ffbf00','#70cac1','#659d4e','#208cc2','#4d6cb1','#584999','#8e559e','#cf3650','#f65337','#fe7139','#ffa433','#ffc25b','#f8e54b'];
        const data = await this.orm.call('hr.employee', 'get_department_leave', []);
        if (!data) return;

        const fData = data[0];
        const dept = data[1];

        fData.forEach(d => {
            d.total = Object.values(d.leave).reduce((a, b) => a + b, 0);
        });

        new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: fData.map(d => d.l_month),
                datasets: [{
                    label: 'Total Leaves',
                    data: fData.map(d => d.total),
                    backgroundColor: '#ff618a',
                }]
            },
            options: { responsive: true }
        });

        const pieData = dept.map(d => ({
            type: d,
            leave: fData.reduce((acc, t) => acc + (t.leave[d] || 0), 0)
        }));

        new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: pieData.map(d => d.type),
                datasets: [{
                    data: pieData.map(d => d.leave),
                    backgroundColor: colors,
                }]
            },
            options: { responsive: true }
        });
    },

    async update_join_resign_trends() {
        const ctx = safeGetContext('lineChart');
        if (!ctx) return;

        const colors = ['#70cac1','#659d4e','#208cc2','#4d6cb1','#584999','#8e559e','#cf3650','#f65337','#fe7139','#ffa433','#ffc25b','#f8e54b'];
        const data = await this.orm.call('hr.employee', 'join_resign_trends', []);
        if (!data) return;

        const labels = data[0].values.map(d => d.l_month);
        const datasets = data.map((ds, i) => ({
            label: ds.name,
            data: ds.values.map(d => d.count),
            borderColor: colors[i % colors.length],
            fill: false,
            tension: 0.1
        }));

        new Chart(ctx, {
            type: 'line',
            data: { labels, datasets },
            options: { responsive: true }
        });
    },

    async update_monthly_attrition() {
        const ctx = safeGetContext('attritionRateChart');
        if (!ctx) return;

        const colors = ['#70cac1','#659d4e','#208cc2','#4d6cb1','#584999','#8e559e','#cf3650','#f65337','#fe7139','#ffa433','#ffc25b','#f8e54b'];
        const data = await this.orm.call('hr.employee', 'get_attrition_rate', []);
        if (!data) return;

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.month),
                datasets: [{
                    label: 'Attrition Rate',
                    data: data.map(d => d.attrition_rate),
                    backgroundColor: colors[0],
                    borderColor: colors[0],
                    fill: false,
                    tension: 0.1,
                }]
            },
            options: { responsive: true }
        });
    },

    async update_leave_trend() {
        const ctx = safeGetContext('leaveTrendChart');
        if (!ctx) return;

        const data = await this.orm.call('hr.employee', 'employee_leave_trend', []);
        if (!data) return;

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.l_month),
                datasets: [{
                    label: 'Leaves Taken',
                    data: data.map(d => d.leave),
                    backgroundColor: 'rgba(70, 140, 193, 0.4)',
                    borderColor: 'rgba(70, 140, 193, 1)',
                    fill: true,
                    tension: 0.1
                }]
            },
            options: { responsive: true }
        });
    },

    async render_employee_skill() {
        const ctx = safeGetContext('skillChart');
        if (!ctx) return;

        const colors = ['#ff6384','#4bc0c0','#ffcd56','#c9cbcf','#36a2eb', '#659d4e', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139', '#ffa433', '#ffc25b', '#f8e54b'];
        const data = await this.orm.call('hr.employee', 'get_employee_skill', []);
        if (!data) return;

        new Chart(ctx, {
            type: 'polarArea',
            data: {
                labels: data.map(d => d.skills),
                datasets: [{
                    data: data.map(d => d.progress),
                    backgroundColor: colors
                }]
            },
            options: { responsive: true }
        });
    },
});
