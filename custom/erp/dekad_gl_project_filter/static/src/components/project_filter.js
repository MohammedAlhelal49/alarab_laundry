/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useState, onWillStart } from "@odoo/owl";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

/**
 * Project & Task filter for General Ledger.
 *
 * Task dropdown shows:
 *   ▼ Task A  (parent task)
 *        Sub-task A1
 *        Sub-task A2
 *   ▼ Task B
 *        Sub-task B1
 *
 * Selecting a parent task selects it + all its sub-tasks.
 * Selecting a sub-task selects it individually.
 * filter_task_ids always contains the actual task ids to filter on.
 */
patch(AccountReportFilters.prototype, {

    setup() {
        super.setup(...arguments);

        this.glFilterState = useState({
            projects: [],
            // tasks[projectId] = [{ id, name, subtasks: [{id, name}] }]
            tasks: {},
            tasksLoading: false,
        });

        onWillStart(async () => {
            if (!('filter_project_id' in this.controller.options)) return;
            const results = await this.env.services.orm.searchRead(
                "project.project",
                [],
                ["id", "name"],
                { limit: 200, order: "name asc" }
            );
            this.glFilterState.projects = results;

            const pid = this.controller.options.filter_project_id;
            if (pid) await this._loadTasks(pid);
        });
    },

    // =========================================================================
    // Getters
    // =========================================================================

    get hasProjectFilter() {
        return 'filter_project_id' in this.controller.options;
    },

    get selectedProjectLabel() {
        const pid = this.controller.options.filter_project_id;
        if (!pid) return _t("Project");
        const found = this.glFilterState.projects.find(p => p.id === pid);
        return found ? found.name : _t("Project");
    },

    get selectedTasksLabel() {
        const ids = this.controller.options.filter_task_ids || [];
        if (!ids.length) return _t("Tasks");
        return _t("%s Task(s)", ids.length);
    },

    get projectIsSelected() {
        return !!this.controller.options.filter_project_id;
    },

    // =========================================================================
    // Data loaders
    // =========================================================================

    async _loadTasks(projectId) {
        if (!projectId) return;
        if (this.glFilterState.tasks[projectId] !== undefined) return;

        this.glFilterState.tasksLoading = true;

        // Load parent tasks
        const parents = await this.env.services.orm.searchRead(
            "project.task",
            [["project_id", "=", projectId], ["parent_id", "=", false]],
            ["id", "name"],
            { limit: 200, order: "name asc" }
        );

        // Load sub-tasks level 1 for all parent tasks in one query
        const parentIds = parents.map(t => t.id);
        let subtasks = [];
        if (parentIds.length) {
            subtasks = await this.env.services.orm.searchRead(
                "project.task",
                [["parent_id", "in", parentIds]],
                ["id", "name", "parent_id"],
                { limit: 500, order: "name asc" }
            );
        }

        // Group sub-tasks under their parent
        const subtasksByParent = {};
        for (const st of subtasks) {
            const pid2 = st.parent_id[0];
            if (!subtasksByParent[pid2]) subtasksByParent[pid2] = [];
            subtasksByParent[pid2].push({ id: st.id, name: st.name });
        }

        const tree = parents.map(t => ({
            id: t.id,
            name: t.name,
            subtasks: subtasksByParent[t.id] || [],
        }));

        this.glFilterState.tasks = {
            ...this.glFilterState.tasks,
            [projectId]: tree,
        };
        this.glFilterState.tasksLoading = false;
    },

    // =========================================================================
    // Helpers
    // =========================================================================

    /** All sub-task ids for a given parent task id */
    _getSubtaskIds(projectId, parentId) {
        const tree = this.glFilterState.tasks[projectId] || [];
        const parent = tree.find(t => t.id === parentId);
        return parent ? parent.subtasks.map(s => s.id) : [];
    },

    /** True if all sub-tasks of a parent are selected */
    _isParentFullySelected(projectId, parentId) {
        const selected = this.controller.options.filter_task_ids || [];
        const subtaskIds = this._getSubtaskIds(projectId, parentId);
        if (!subtaskIds.length) return selected.includes(parentId);
        return subtaskIds.every(id => selected.includes(id));
    },

    /** True if some (but not all) sub-tasks of a parent are selected */
    _isParentPartiallySelected(projectId, parentId) {
        const selected = this.controller.options.filter_task_ids || [];
        const subtaskIds = this._getSubtaskIds(projectId, parentId);
        if (!subtaskIds.length) return false;
        return subtaskIds.some(id => selected.includes(id)) && !this._isParentFullySelected(projectId, parentId);
    },

    // =========================================================================
    // Actions
    // =========================================================================

    async selectProject(projectId) {
        const current = this.controller.options.filter_project_id;
        const newId = (projectId && current === projectId) ? false : projectId;
        await this.controller.updateOption("filter_project_id", newId);
        await this.controller.updateOption("filter_task_ids", []);
        if (newId) await this._loadTasks(newId);
        await this.applyFilters("filter_project_id", 0);
    },

    /**
     * Toggle a parent task:
     * - If all its sub-tasks are selected → deselect all
     * - Otherwise → select all sub-tasks (and the parent itself if no subtasks)
     */
    async toggleParentTask(projectId, taskId) {
        const current = [...(this.controller.options.filter_task_ids || [])];
        const subtaskIds = this._getSubtaskIds(projectId, taskId);

        if (subtaskIds.length) {
            const allSelected = subtaskIds.every(id => current.includes(id));
            if (allSelected) {
                // Deselect all sub-tasks
                const next = current.filter(id => !subtaskIds.includes(id));
                await this.controller.updateOption("filter_task_ids", next);
            } else {
                // Select all sub-tasks not yet selected
                const next = [...new Set([...current, ...subtaskIds])];
                await this.controller.updateOption("filter_task_ids", next);
            }
        } else {
            // No sub-tasks — toggle the parent task itself
            const idx = current.indexOf(taskId);
            if (idx === -1) current.push(taskId);
            else current.splice(idx, 1);
            await this.controller.updateOption("filter_task_ids", current);
        }
        await this.applyFilters("filter_task_ids", 0);
    },

    /** Toggle an individual sub-task */
    async toggleTask(taskId) {
        const current = [...(this.controller.options.filter_task_ids || [])];
        const idx = current.indexOf(taskId);
        if (idx === -1) current.push(taskId);
        else current.splice(idx, 1);
        await this.controller.updateOption("filter_task_ids", current);
        await this.applyFilters("filter_task_ids", 0);
    },

    async clearTasks() {
        await this.controller.updateOption("filter_task_ids", []);
        await this.applyFilters("filter_task_ids", 0);
    },
});