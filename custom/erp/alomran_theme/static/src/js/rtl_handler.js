/**
 * RTL Handler for Al Omran Theme
 * This script handles RTL detection and applies necessary adjustments
 */

(function() {
    'use strict';

    // RTL Handler Class
    class RTLHandler {
        constructor() {
            this.isRTL = this.detectRTL();
            this.init();
        }

        /**
         * Detect if current page should be RTL
         */
        detectRTL() {
            // Check HTML dir attribute
            const htmlDir = document.documentElement.getAttribute('dir');
            if (htmlDir === 'rtl') return true;

            // Check HTML lang attribute
            const htmlLang = document.documentElement.getAttribute('lang');
            if (htmlLang && htmlLang.startsWith('ar')) return true;

            // Check body class
            if (document.body.classList.contains('rtl-mode')) return true;

            // Check URL for Arabic language indicator
            const url = window.location.href;
            if (url.includes('/ar/') || url.includes('/ar_') || url.includes('lang=ar')) return true;

            // Check for Odoo language cookie
            const cookies = document.cookie;
            if (cookies.includes('frontend_lang=ar')) return true;

            return false;
        }

        /**
         * Initialize RTL handling
         */
        init() {
            if (this.isRTL) {
                this.applyRTL();
            }

            // Watch for language changes
            this.observeLanguageChanges();
        }

        /**
         * Apply RTL styles and attributes
         */
        applyRTL() {
            // Set HTML attributes
            document.documentElement.setAttribute('dir', 'rtl');
            document.documentElement.setAttribute('lang', 'ar');
            
            // Add RTL class to body
            document.body.classList.add('rtl-mode');
            document.body.classList.remove('ltr-mode');

            // Fix Bootstrap icons that need to be flipped
            this.flipIcons();

            // Fix text alignment issues
            this.fixTextAlignment();

            // Fix floating elements
            this.fixFloatingElements();

            // Trigger custom event
            document.dispatchEvent(new CustomEvent('rtlApplied'));
        }

        /**
         * Apply LTR styles and attributes
         */
        applyLTR() {
            // Set HTML attributes
            document.documentElement.setAttribute('dir', 'ltr');
            
            // Add LTR class to body
            document.body.classList.add('ltr-mode');
            document.body.classList.remove('rtl-mode');

            // Trigger custom event
            document.dispatchEvent(new CustomEvent('ltrApplied'));
        }

        /**
         * Flip directional icons for RTL
         */
        flipIcons() {
            // Icons that should be flipped in RTL
            const iconsToFlip = [
                '.fa-chevron-right',
                '.fa-chevron-left',
                '.fa-arrow-right',
                '.fa-arrow-left',
                '.fa-angle-right',
                '.fa-angle-left',
                '.fa-caret-right',
                '.fa-caret-left'
            ];

            iconsToFlip.forEach(selector => {
                document.querySelectorAll(selector).forEach(icon => {
                    // Don't flip if already handled by CSS
                    if (!icon.classList.contains('rtl-flipped')) {
                        icon.classList.add('rtl-icon');
                    }
                });
            });
        }

        /**
         * Fix text alignment for specific elements
         */
        fixTextAlignment() {
            // Elements that should have RTL text alignment
            const rtlElements = [
                '.hero-content',
                '.about-description',
                '.section-content',
                '.card-body',
                '.modal-body',
                'footer'
            ];

            rtlElements.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    if (!el.hasAttribute('data-rtl-processed')) {
                        el.setAttribute('data-rtl-processed', 'true');
                    }
                });
            });
        }

        /**
         * Fix floating elements position for RTL
         */
        fixFloatingElements() {
            // Floating action buttons
            const floatingActions = document.querySelector('.o_floating_actions');
            if (floatingActions) {
                floatingActions.classList.add('rtl-positioned');
            }

            // Experience badges
            document.querySelectorAll('.experience-badge').forEach(badge => {
                badge.classList.add('rtl-positioned');
            });
        }

        /**
         * Observe DOM for language changes
         */
        observeLanguageChanges() {
            // Watch for attribute changes on HTML element
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'attributes') {
                        if (mutation.attributeName === 'dir' || mutation.attributeName === 'lang') {
                            this.isRTL = this.detectRTL();
                            if (this.isRTL) {
                                this.applyRTL();
                            } else {
                                this.applyLTR();
                            }
                        }
                    }
                });
            });

            observer.observe(document.documentElement, {
                attributes: true,
                attributeFilter: ['dir', 'lang']
            });
        }

        /**
         * Toggle RTL mode manually
         */
        toggleRTL() {
            this.isRTL = !this.isRTL;
            if (this.isRTL) {
                this.applyRTL();
            } else {
                this.applyLTR();
            }
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.rtlHandler = new RTLHandler();
        });
    } else {
        window.rtlHandler = new RTLHandler();
    }

    // Expose toggle function globally
    window.toggleRTL = function() {
        if (window.rtlHandler) {
            window.rtlHandler.toggleRTL();
        }
    };

    // Handle dynamic content loading (e.g., AJAX)
    document.addEventListener('contentLoaded', function() {
        if (window.rtlHandler && window.rtlHandler.isRTL) {
            window.rtlHandler.flipIcons();
            window.rtlHandler.fixTextAlignment();
        }
    });

})();
