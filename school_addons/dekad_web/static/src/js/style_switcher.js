/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Style Switcher Widget
 * Allows users to toggle between two different style themes
 */
publicWidget.registry.StyleSwitcher = publicWidget.Widget.extend({
    selector: '.o_portal_wrap, body',
    events: {
        'click .style-switcher-btn': '_onStyleSwitch',
    },

    /**
     * Initialize the widget
     */
    start: function () {
        this._super.apply(this, arguments);
        this._initializeStyleSwitcher();
        return this._super.apply(this, arguments);
    },

    /**
     * Initialize the style switcher on page load
     */
    _initializeStyleSwitcher: function () {
        // Get saved style preference from localStorage
        const savedStyle = localStorage.getItem('portal_style_theme') || 'style1';

        // Apply the saved style
        this._applyStyle(savedStyle);

        // Update button state
        this._updateButtonState(savedStyle);
    },

    /**
     * Handle style switch button click
     */
    _onStyleSwitch: function (ev) {
        ev.preventDefault();

        const $button = $(ev.currentTarget);
        const currentStyle = $('body').hasClass('style-theme-2') ? 'style2' : 'style1';
        const newStyle = currentStyle === 'style1' ? 'style2' : 'style1';

        // Apply new style with animation
        this._applyStyleWithAnimation(newStyle);

        // Save preference
        localStorage.setItem('portal_style_theme', newStyle);

        // Update button
        this._updateButtonState(newStyle);

        // Show notification
        this._showStyleChangeNotification(newStyle);
    },

    /**
     * Apply style theme
     */
    _applyStyle: function (style) {
        $('body').removeClass('style-theme-1 style-theme-2');

        if (style === 'style2') {
            $('body').addClass('style-theme-2');
        } else {
            $('body').addClass('style-theme-1');
        }
    },

    /**
     * Apply style with smooth transition animation
     */
    _applyStyleWithAnimation: function (style) {
        // Add transition class
        $('body').addClass('style-transitioning');

        // Fade out
        $('body').css('opacity', '0.7');

        setTimeout(() => {
            this._applyStyle(style);

            // Fade back in
            $('body').css('opacity', '1');

            setTimeout(() => {
                $('body').removeClass('style-transitioning');
            }, 300);
        }, 150);
    },

    /**
     * Update button state and icon
     */
    _updateButtonState: function (style) {
        const $button = $('.style-switcher-btn');
        const $icon = $button.find('i');
        const $text = $button.find('.btn-text');

        if (style === 'style2') {
            $icon.removeClass('fa-palette').addClass('fa-sun');
            $text.text(_t('Classic Style'));
            $button.attr('title', _t('Switch to Classic Style'));
        } else {
            $icon.removeClass('fa-sun').addClass('fa-palette');
            $text.text(_t('Modern Style'));
            $button.attr('title', _t('Switch to Modern Style'));
        }
    },

    /**
     * Show notification when style changes
     */
    _showStyleChangeNotification: function (style) {
        const styleName = style === 'style2' ? _t('Modern Style') : _t('Classic Style');

        // Check if toastr is available
        if (typeof toastr !== 'undefined') {
            toastr.success(_t('Switched to ') + styleName, _t('Style Changed'), {
                timeOut: 2000,
                progressBar: true,
            });
        } else {
            // Fallback to simple alert
            const message = _t('Style changed to: ') + styleName;
            this._showSimpleNotification(message);
        }
    },

    /**
     * Simple notification fallback
     */
    _showSimpleNotification: function (message) {
        const $notification = $(`
            <div class="style-notification">
                <i class="fa fa-check-circle"></i>
                <span>${message}</span>
            </div>
        `);

        $('body').append($notification);

        setTimeout(() => {
            $notification.addClass('show');
        }, 10);

        setTimeout(() => {
            $notification.removeClass('show');
            setTimeout(() => $notification.remove(), 300);
        }, 2500);
    },
});

export default publicWidget.registry.StyleSwitcher;