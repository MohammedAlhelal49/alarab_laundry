/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";

/**
 * Vertical Navigation in Editable Lists for Sale & Purchase Orders
 */

const ALLOWED_MODELS = [
    'sale.order.line',
    'purchase.order.line',
];

// Patch ListRenderer for handling Enter key
patch(ListRenderer.prototype, {
    /**
     * Handle keyboard navigation
     */
    onCellKeydown(ev) {
        // Check if this is an allowed model
        const resModel = this.props.list?.resModel || '';
        
        if (!ALLOWED_MODELS.includes(resModel)) {
            return super.onCellKeydown?.(...arguments);
        }

        // Only intercept Enter key without modifiers
        if (ev.key === 'Enter' && !ev.shiftKey && !ev.ctrlKey && !ev.altKey && !ev.metaKey) {
            const cell = ev.target.closest('.o_data_cell');
            const row = ev.target.closest('.o_data_row');
            
            if (cell && row) {
                const cells = Array.from(row.querySelectorAll('.o_data_cell'));
                const colIndex = cells.indexOf(cell);
                const nextRow = row.nextElementSibling;
                
                if (nextRow && nextRow.classList.contains('o_data_row') && colIndex !== -1) {
                    const nextCells = nextRow.querySelectorAll('.o_data_cell');
                    const targetCell = nextCells[colIndex];
                    
                    if (targetCell) {
                        ev.preventDefault();
                        ev.stopPropagation();
                        
                        // Click to activate the cell
                        targetCell.click();
                        
                        // Focus input after a short delay
                        setTimeout(() => {
                            const input = targetCell.querySelector('input, textarea, select, .o_input');
                            if (input) {
                                input.focus();
                                if (input.select) input.select();
                            }
                        }, 50);
                        
                        return;
                    }
                }
            }
        }
        
        // Default behavior
        if (super.onCellKeydown) {
            return super.onCellKeydown(...arguments);
        }
    },
});

// Global event listener as fallback
document.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter' || ev.shiftKey || ev.ctrlKey || ev.altKey || ev.metaKey) {
        return;
    }
    
    // Check if we're in a sale or purchase order line
    const cell = ev.target.closest('.o_data_cell');
    const row = ev.target.closest('.o_data_row');
    const form = ev.target.closest('.o_form_view');
    
    if (!cell || !row || !form) {
        return;
    }
    
    // Check if it's sale or purchase form
    const isSaleOrPurchase = form.querySelector('.o_field_widget[name="order_line"]') || 
                             form.querySelector('.o_field_widget[name="invoice_line_ids"]');
    
    if (!isSaleOrPurchase) {
        return;
    }
    
    const cells = Array.from(row.querySelectorAll('.o_data_cell'));
    const colIndex = cells.indexOf(cell);
    const nextRow = row.nextElementSibling;
    
    if (nextRow && nextRow.classList.contains('o_data_row') && colIndex !== -1) {
        const nextCells = nextRow.querySelectorAll('.o_data_cell');
        const targetCell = nextCells[colIndex];
        
        if (targetCell) {
            ev.preventDefault();
            ev.stopPropagation();
            
            targetCell.click();
            
            setTimeout(() => {
                const input = targetCell.querySelector('input, textarea, select, .o_input');
                if (input) {
                    input.focus();
                    if (input.select) input.select();
                }
            }, 50);
        }
    }
}, true);
