/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.AssignmentPortalWidget = publicWidget.Widget.extend({
    selector: '.portal-page-content, .dynamic-website-card-holder',
    events: {
        'click .file-update-trigger': '_onFileUpdateTrigger',
        'click .clear-icon': '_onClearFile',
        'change input[type="file"]': '_onFileChange',
    },

    /**
     * Handle the "Change" button click for file updates
     */
    _onFileUpdateTrigger: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        const $trigger = $(ev.currentTarget);
        const $container = $trigger.closest('.file-field-container, .update-file-holder');
        const $fileInput = $container.find('input[type="file"]');
        const $clearIcon = $container.find('.clear-icon');

        // Show the file input and clear icon
        $fileInput.removeClass('hidden-file').show();
        $clearIcon.removeClass('hidden-file').show();

        // Hide the "Change" button and file info
        $trigger.hide();
        $trigger.siblings('t, a, i').hide();

        // Trigger the file input click to open file chooser
        $fileInput[0].click();
    },

    /**
     * Handle the "Clear" icon click
     */
    _onClearFile: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        const $clearIcon = $(ev.currentTarget);
        const $container = $clearIcon.closest('.file-field-container, .update-file-holder');
        const $fileInput = $container.find('input[type="file"]');

        // Clear the file input value
        $fileInput.val('');

        // If we're in update mode with existing file, restore the original view
        const $updateTrigger = $container.find('.file-update-trigger');
        if ($updateTrigger.length > 0) {
            $fileInput.addClass('hidden-file').hide();
            $clearIcon.addClass('hidden-file').hide();
            $updateTrigger.show();
            $updateTrigger.siblings('t, a, i').show();
        }
    },

    /**
     * Handle file input change (when user selects a file)
     */
    _onFileChange: function (ev) {
        const $fileInput = $(ev.currentTarget);
        const $container = $fileInput.closest('.file-field-container, .update-file-holder');
        const file = $fileInput[0].files[0];

        if (file) {
            // Check file size (2MB limit)
            const maxSize = 2 * 1024 * 1024; // 2MB in bytes
            if (file.size > maxSize) {
                alert(_t('File size must be less than 2MB. Please select a smaller file.'));
                $fileInput.val('');
                return;
            }

            // Show file name near the input
            const fileName = file.name;
            let $fileNameDisplay = $container.find('.selected-file-name');

            if ($fileNameDisplay.length === 0) {
                $fileNameDisplay = $('<span class="selected-file-name"></span>');
                $fileInput.after($fileNameDisplay);
            }

            $fileNameDisplay.text(fileName).show();
        }
    },
});

export default publicWidget.registry.AssignmentPortalWidget;