/** @odoo-module */

/**
 * Twitter Bootstrap Extensions for Dekad Web
 * This file wraps Bootstrap functionality for Odoo 18
 */

odoo.define('dekad_web.twitter_bootstrap', function (require) {
    'use strict';

    // Import required Odoo modules
    const publicWidget = require('web.public.widget');
    const core = require('web.core');
    const _t = core._t;

    /**
     * Bootstrap Extensions Widget
     * Enhances Bootstrap components with custom functionality
     */
    publicWidget.registry.DekadBootstrapExtensions = publicWidget.Widget.extend({
        selector: 'body',

        /**
         * @override
         */
        start: function () {
            const self = this;
            return this._super.apply(this, arguments).then(function () {
                self._initializeBootstrapExtensions();
            });
        },

        /**
         * Initialize Bootstrap extensions
         */
        _initializeBootstrapExtensions: function () {
            this._enhanceTooltips();
            this._enhancePopovers();
            this._enhanceModals();
            this._enhanceDropdowns();
        },

        /**
         * Enhance Bootstrap tooltips with custom options
         */
        _enhanceTooltips: function () {
            // Initialize all tooltips with data-toggle="tooltip"
            $('[data-toggle="tooltip"], [data-bs-toggle="tooltip"]').tooltip({
                trigger: 'hover',
                html: true,
                container: 'body',
                boundary: 'window'
            });

            // Custom tooltip for Dekad elements
            $('.dekad-tooltip').tooltip({
                placement: 'top',
                trigger: 'hover focus',
                delay: { show: 500, hide: 100 }
            });
        },

        /**
         * Enhance Bootstrap popovers
         */
        _enhancePopovers: function () {
            $('[data-toggle="popover"], [data-bs-toggle="popover"]').popover({
                trigger: 'click',
                html: true,
                container: 'body',
                sanitize: false  // Allow HTML content
            });

            // Dismiss popovers on outside click
            $('body').on('click', function (e) {
                $('[data-toggle="popover"], [data-bs-toggle="popover"]').each(function () {
                    if (!$(this).is(e.target) &&
                        $(this).has(e.target).length === 0 &&
                        $('.popover').has(e.target).length === 0) {
                        $(this).popover('hide');
                    }
                });
            });
        },

        /**
         * Enhance Bootstrap modals
         */
        _enhanceModals: function () {
            // Auto-focus first input in modal
            $('.modal').on('shown.bs.modal', function () {
                $(this).find('input:first').focus();
            });

            // Clear form data on modal close
            $('.modal').on('hidden.bs.modal', function () {
                const $forms = $(this).find('form');
                if ($forms.length && $forms.data('auto-reset') !== false) {
                    $forms[0].reset();
                }
            });

            // Handle dynamic modal content
            $('[data-dekad-modal]').on('click', function (e) {
                e.preventDefault();
                const modalId = $(this).data('dekad-modal');
                const $modal = $('#' + modalId);

                if ($modal.length) {
                    $modal.modal('show');
                }
            });
        },

        /**
         * Enhance Bootstrap dropdowns
         */
        _enhanceDropdowns: function () {
            // Keep dropdown open on inside click
            $('.dropdown-menu.keep-open').on('click', function (e) {
                e.stopPropagation();
            });

            // Multi-level dropdown support
            $('.dropdown-submenu > a').on('click', function (e) {
                e.preventDefault();
                e.stopPropagation();

                const $submenu = $(this).next('.dropdown-menu');
                $submenu.toggleClass('show');

                // Close other submenus at the same level
                $(this).parent().siblings().find('.dropdown-menu').removeClass('show');
            });

            // Close submenus when main dropdown closes
            $('.dropdown').on('hidden.bs.dropdown', function () {
                $(this).find('.dropdown-submenu .dropdown-menu').removeClass('show');
            });
        }
    });

    /**
     * Bootstrap Utilities
     * Additional utility functions for Bootstrap components
     */
    const BootstrapUtils = {
        /**
         * Show a Bootstrap alert
         * @param {String} message - Alert message
         * @param {String} type - Alert type (success, danger, warning, info)
         * @param {Boolean} dismissible - Whether alert is dismissible
         */
        showAlert: function (message, type = 'info', dismissible = true) {
            const alertClass = dismissible ? 'alert-dismissible fade show' : '';
            const closeBtn = dismissible ?
                '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' : '';

            const alertHtml = `
                <div class="alert alert-${type} ${alertClass}" role="alert">
                    ${message}
                    ${closeBtn}
                </div>
            `;

            // Append to alert container or body
            const $container = $('.dekad-alerts-container').length ?
                $('.dekad-alerts-container') : $('body');

            const $alert = $(alertHtml).prependTo($container);

            // Auto-dismiss after 5 seconds
            if (dismissible) {
                setTimeout(function () {
                    $alert.alert('close');
                }, 5000);
            }

            return $alert;
        },

        /**
         * Show a confirmation modal
         * @param {String} title - Modal title
         * @param {String} message - Modal message
         * @param {Function} onConfirm - Callback on confirmation
         * @param {Function} onCancel - Callback on cancellation
         */
        showConfirmModal: function (title, message, onConfirm, onCancel) {
            const modalHtml = `
                <div class="modal fade" tabindex="-1" role="dialog">
                    <div class="modal-dialog" role="document">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">${title}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <p>${message}</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                    ${_t('Cancel')}
                                </button>
                                <button type="button" class="btn btn-primary btn-confirm">
                                    ${_t('Confirm')}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            const $modal = $(modalHtml).appendTo('body');

            $modal.on('click', '.btn-confirm', function () {
                if (onConfirm) onConfirm();
                $modal.modal('hide');
            });

            $modal.on('hidden.bs.modal', function () {
                if (onCancel) onCancel();
                $modal.remove();
            });

            $modal.modal('show');

            return $modal;
        },

        /**
         * Initialize a progress bar
         * @param {jQuery} $element - Progress bar element
         * @param {Number} value - Initial value (0-100)
         * @param {String} type - Progress bar type (success, info, warning, danger)
         */
        initProgressBar: function ($element, value = 0, type = 'primary') {
            if (!$element.length) return;

            const $progressBar = $element.find('.progress-bar').length ?
                $element.find('.progress-bar') : $element;

            $progressBar
                .removeClass('bg-success bg-info bg-warning bg-danger bg-primary')
                .addClass('bg-' + type)
                .css('width', value + '%')
                .attr('aria-valuenow', value)
                .text(value + '%');

            return $progressBar;
        },

        /**
         * Update progress bar value with animation
         * @param {jQuery} $progressBar - Progress bar element
         * @param {Number} newValue - New value (0-100)
         * @param {Number} duration - Animation duration in ms
         */
        updateProgressBar: function ($progressBar, newValue, duration = 500) {
            const currentValue = parseInt($progressBar.attr('aria-valuenow') || 0);

            $({ value: currentValue }).animate({ value: newValue }, {
                duration: duration,
                step: function (now) {
                    const value = Math.round(now);
                    $progressBar
                        .css('width', value + '%')
                        .attr('aria-valuenow', value)
                        .text(value + '%');
                }
            });
        }
    };

    // Expose utilities globally for other modules
    publicWidget.registry.DekadBootstrapExtensions.utils = BootstrapUtils;

    return publicWidget.registry.DekadBootstrapExtensions;
});