/** @odoo-module **/

/**
 * Dekad Web - Pure JavaScript Implementation for Odoo 18
 * Fixed version with working file "Change" and "Clear" features
 * No jQuery dependencies - Following Odoo 18 best practices
 */

import { whenReady } from "@odoo/owl";

class DekadWebHandler {
    constructor() {
        this.initialized = false;
        this.init();
    }

    init() {
        if (this.initialized) return;

        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }

        this.initialized = true;
    }

    setup() {
        this.initDatePickers();
        this.initPasswordToggles();
        this.initFileHandlers();
        this.initAnimations();
        this.initToastrConfig();
        this.initLightboxConfig();
    }

    /** Initialize native HTML5 date pickers **/
    initDatePickers() {
        document.querySelectorAll('.text-input-date-picker').forEach(input => {
            const originalValue = input.value;
            input.type = 'date';
            if (originalValue && originalValue.includes('/')) {
                const [day, month, year] = originalValue.split('/');
                if (day && month && year) {
                    input.value = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
                }
            }

            input.addEventListener('change', (e) => {
                const date = e.target.value;
                if (date) {
                    const [year, month, day] = date.split('-');
                    e.target.dataset.formattedDate = `${day}/${month}/${year}`;
                }
            });
        });

        document.querySelectorAll('.handle-server-date-formate').forEach(input => {
            const value = input.value;
            if (value && value.match(/^\d{4}-\d{2}-\d{2}$/)) {
                const [year, month, day] = value.split('-');
                input.value = `${day}/${month}/${year}`;
            }
        });
    }

    /** Password visibility toggle **/
    initPasswordToggles() {
        document.addEventListener('click', (e) => {
            const icon = e.target.closest('form input[type="password"] + .fa, form input[type="text"][data-password-field] + .fa');
            if (icon) {
                e.preventDefault();
                const input = icon.previousElementSibling;
                if (!input) return;

                if (input.type === 'password') {
                    input.type = 'text';
                    input.setAttribute('data-password-field', 'true');
                    icon.classList.replace('fa-eye', 'fa-eye-slash');
                } else {
                    input.type = 'password';
                    input.removeAttribute('data-password-field');
                    icon.classList.replace('fa-eye-slash', 'fa-eye');
                }
            }
        });
    }

    /** Fixed file handlers **/
    initFileHandlers() {
        // Clear file button
        document.addEventListener('click', (e) => {
            if (e.target.matches('.file-field-container .clear-icon')) {
                e.preventDefault();
                const container = e.target.closest('.file-field-container');
                const fileInput = container?.querySelector('input[type="file"]');
                if (fileInput) {
                    fileInput.value = '';
                    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        });

        // Change file button
        document.addEventListener('click', (e) => {
            if (e.target.matches('.file-update-trigger')) {
                e.preventDefault();
                const container = e.target.closest('.file-field-container');
                if (!container) return;

                const fileInput = container.querySelector('input[type="file"]');
                const clearIcon = container.querySelector('.clear-icon');

                // Reveal input and clear button
                if (fileInput) fileInput.classList.remove('hidden-file');
                if (clearIcon) clearIcon.classList.remove('hidden-file');

                // Hide "Change" button
                e.target.style.display = 'none';
            }
        });

        // Link navigation (update, delete)
        document.addEventListener('click', (e) => {
            const link = e.target.closest('.form-update-link');
            if (link) {
                e.preventDefault();
                const href = link.getAttribute('href');
                if (href) window.location.href = href;
            }
        });
    }

    /** Page fade animation **/
    initAnimations() {
        const fadeElements = document.querySelectorAll('.page-fade-animate');
        if (fadeElements.length > 0) {
            requestAnimationFrame(() => {
                fadeElements.forEach(el => {
                    el.style.transition = 'opacity 1s ease-in-out';
                    el.style.opacity = '1';
                });
            });
        }
    }

    /** Configure Toastr **/
    initToastrConfig() {
        if (typeof window.toastr !== 'undefined') {
            window.toastr.options = {
                closeButton: true,
                progressBar: true,
                positionClass: 'toast-top-right',
                timeOut: 5000,
            };
            window.dekadNotify = {
                success: (msg, title = '') => window.toastr.success(msg, title),
                error: (msg, title = '') => window.toastr.error(msg, title),
                warning: (msg, title = '') => window.toastr.warning(msg, title),
                info: (msg, title = '') => window.toastr.info(msg, title),
            };
        }
    }

    /** Configure Lightbox **/
    initLightboxConfig() {
        if (typeof window.lightbox !== 'undefined') {
            window.lightbox.option({
                resizeDuration: 200,
                wrapAround: true,
                albumLabel: 'Image %1 of %2',
                fadeDuration: 500,
                imageFadeDuration: 600,
                positionFromTop: 50,
                disableScrolling: true
            });
        }
    }

    /** Date formatting utility **/
    formatDate(dateString, fromFormat = 'YYYY-MM-DD', toFormat = 'DD/MM/YYYY') {
        if (!dateString) return '';
        let date;
        if (fromFormat === 'YYYY-MM-DD') {
            const [year, month, day] = dateString.split('-');
            date = new Date(year, month - 1, day);
        } else if (fromFormat === 'DD/MM/YYYY') {
            const [day, month, year] = dateString.split('/');
            date = new Date(year, month - 1, day);
        }
        if (!date || isNaN(date)) return dateString;

        const dd = String(date.getDate()).padStart(2, '0');
        const mm = String(date.getMonth() + 1).padStart(2, '0');
        const yyyy = date.getFullYear();
        return toFormat === 'DD/MM/YYYY' ? `${dd}/${mm}/${yyyy}` : `${yyyy}-${mm}-${dd}`;
    }
}

/** Initialize after Odoo and OWL are ready **/
whenReady(() => {
    console.log('Dekad Web Module loaded for Odoo 18 (fixed version)');
    const handler = new DekadWebHandler();
    window.dekadWeb = handler;
});