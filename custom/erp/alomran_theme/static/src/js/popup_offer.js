/** @odoo-module **/

/**
 * Alomran Theme - Popup Offer Module (Multi-Language Support)
 * ===========================================================
 * Handles website popup offers display and form submission.
 * Fully dynamic content based on server-side language detection.
 *
 * Features:
 * - Full Arabic/English support
 * - Dynamic content from backend
 * - RTL/LTR layout support
 * - ✅ CSRF token support (Odoo compatible)
 * - Secure cookie handling
 * - Countdown timer
 * - Exit intent detection
 */

(function() {
    'use strict';

    // ============================================================
    // CONFIGURATION
    // ============================================================

    const CONFIG = {
        DEBUG: false,
        COOKIE_NAME: 'alomran_popup_shown',
        COOKIE_SECURE: window.location.protocol === 'https:',
        PHONE_PATTERNS: [
            /^(?:\+971|00971|971)?(?:50|51|52|54|55|56|58)\d{7}$/,
            /^(?:\+966|00966|966)?5\d{8}$/,
            /^05\d{8}$/,
            /^5\d{8}$/
        ]
    };

    // ============================================================
    // UTILITY FUNCTIONS
    // ============================================================

    function log(...args) {
        if (CONFIG.DEBUG) {
            console.log('[AlomranPopup]', ...args);
        }
    }

    function validatePhone(phone) {
        if (!phone) return false;
        const cleaned = phone.replace(/[\s\-\(\)\+]/g, '');
        return CONFIG.PHONE_PATTERNS.some(p => p.test(cleaned));
    }

    // ============================================================
    // COOKIE FUNCTIONS (Secure)
    // ============================================================

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return null;
    }

    function setCookie(name, value, days) {
        const expires = new Date();
        expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));

        let cookieString = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Lax`;

        if (CONFIG.COOKIE_SECURE) {
            cookieString += ';Secure';
        }

        document.cookie = cookieString;
    }

    // ============================================================
    // POPUP CLASS
    // ============================================================

    class PopupHandler {
        constructor() {
            this.settings = null;
            this.countdownInterval = null;
            this.exitIntentShown = false;
            this.isSubmitting = false;
            this.isEnglish = false;
            this.isRtl = true;
            this.init();
        }

        init() {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.start());
            } else {
                this.start();
            }
        }

        async start() {
            log('Starting popup handler');

            const popupElement = document.getElementById('offerPopup');
            if (!popupElement) {
                log('Popup element not found');
                return;
            }

            if (getCookie(CONFIG.COOKIE_NAME)) {
                log('Popup already shown to user');
                return;
            }

            if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                log('Reduced motion preferred - limiting animations');
            }

            const settings = await this.fetchSettings();
            if (!settings) {
                log('No active offer');
                return;
            }

            this.settings = settings;
            this.isEnglish = settings.is_english || false;
            this.isRtl = settings.is_rtl !== false;

            log('Active offer:', settings.name, '| Language:', this.isEnglish ? 'EN' : 'AR');

            this.applyLanguageDirection();
            this.populatePopup();
            this.setupForm();
            this.setupCloseHandlers();
            this.scheduleDisplay();

            if (settings.exit_intent) {
                this.setupExitIntent();
            }
        }

        /**
         * ✅ Odoo-compatible JSON-RPC call
         * يرسل الـ session cookies تلقائياً للتحقق من CSRF
         */
        async jsonRpc(url, params = {}) {
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: params,
                        id: Math.floor(Math.random() * 1000000000)
                    }),
                    // ✅ مهم جداً: يرسل الـ cookies تلقائياً للتحقق من الـ session
                    credentials: 'same-origin'
                });

                const data = await response.json();

                if (data.error) {
                    log('RPC Error:', data.error);
                    throw new Error(data.error.message || data.error.data?.message || 'RPC Error');
                }

                return data.result;

            } catch (error) {
                log('Fetch error:', error);
                throw error;
            }
        }

        async fetchSettings() {
            try {
                const result = await this.jsonRpc('/popup/settings', {});

                if (result?.active) {
                    return result;
                }

                return null;

            } catch (error) {
                log('Error fetching settings:', error);
                return null;
            }
        }

        applyLanguageDirection() {
            const popupElement = document.getElementById('offerPopup');
            if (!popupElement) return;

            popupElement.setAttribute('dir', this.isRtl ? 'rtl' : 'ltr');
            popupElement.style.direction = this.isRtl ? 'rtl' : 'ltr';

            popupElement.classList.remove('popup-ar', 'popup-en');
            popupElement.classList.add(this.isEnglish ? 'popup-en' : 'popup-ar');

            const formElements = popupElement.querySelectorAll('.form-control, .form-label');
            formElements.forEach(el => {
                el.style.textAlign = this.isRtl ? 'right' : 'left';
            });

            log('Applied language direction:', this.isRtl ? 'RTL' : 'LTR');
        }

        populatePopup() {
            const s = this.settings;

            this.setValue('offerId', s.id);

            const badge = document.getElementById('offerBadge');
            const badgeText = document.getElementById('badgeText');
            if (badge && badgeText) {
                badgeText.textContent = s.badge_text;
                badge.style.background = s.badge_color;
            }

            const icon = document.getElementById('offerIcon');
            if (icon) {
                const iconMap = {
                    'buy_x_get_y': 'fa-gift',
                    'discount_percentage': 'fa-percent',
                    'discount_fixed': 'fa-tag',
                    'free_consultation': 'fa-headset',
                    'custom': 'fa-star'
                };
                icon.className = `fa ${iconMap[s.offer_type] || 'fa-star'}`;
            }

            this.setText('offerTitle', s.title);
            this.setText('offerSubtitle', s.subtitle);
            this.setText('offerDescription', s.description);
            this.setText('socialProofText', s.social_proof);
            this.setText('formTitle', s.form_title);
            this.setText('formSubtitle', s.form_subtitle);
            this.setText('nameLabel', s.name_label);
            this.setText('phoneLabel', s.phone_label);

            this.setPlaceholder('popupName', s.name_placeholder);
            this.setPlaceholder('popupPhone', s.phone_placeholder);

            const termsContainer = document.getElementById('termsContainer');
            const termsText = document.getElementById('termsText');
            if (s.terms && termsContainer && termsText) {
                termsText.textContent = s.terms;
                termsContainer.style.display = 'block';
            } else if (termsContainer) {
                termsContainer.style.display = 'none';
            }

            if (s.show_countdown && s.end_timestamp) {
                this.startCountdown(s.end_timestamp);
            }

            const submitBtn = document.getElementById('submitBtn');
            if (submitBtn) {
                submitBtn.innerHTML = `<i class="fa fa-rocket me-2"></i>${s.submit_btn_text}`;
            }

            this.setText('closeBtnText', s.close_btn_text);
            this.setText('trustText', s.trust_text);
            this.setText('successTitle', s.success_title);

            // Browse courses button text
            this.setText('browseCoursesBtnText', this.isEnglish ? 'Browse Our Courses' : 'تصفح دوراتنا');
            this.setText('closeSuccessBtnText', this.isEnglish ? 'Close' : 'إغلاق');

            log('Popup populated with localized content');
        }

        setText(id, text) {
            const el = document.getElementById(id);
            if (el && text) el.textContent = text;
        }

        setValue(id, value) {
            const el = document.getElementById(id);
            if (el && value !== undefined) el.value = value;
        }

        setPlaceholder(id, placeholder) {
            const el = document.getElementById(id);
            if (el && placeholder) el.placeholder = placeholder;
        }

        startCountdown(endTimestamp) {
            const countdownContainer = document.getElementById('countdownContainer');
            if (!countdownContainer) return;

            countdownContainer.style.display = 'block';

            this.setText('countdownTitle', this.settings.countdown_title);
            this.setText('daysLabel', this.settings.days_label);
            this.setText('hoursLabel', this.settings.hours_label);
            this.setText('minsLabel', this.settings.mins_label);

            const endDate = new Date(endTimestamp);

            const update = () => {
                const now = new Date();
                const diff = endDate - now;

                if (diff <= 0) {
                    clearInterval(this.countdownInterval);
                    countdownContainer.style.display = 'none';
                    return;
                }

                const days = Math.floor(diff / (1000 * 60 * 60 * 24));
                const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

                this.setText('countdownDays', String(days).padStart(2, '0'));
                this.setText('countdownHours', String(hours).padStart(2, '0'));
                this.setText('countdownMins', String(mins).padStart(2, '0'));
            };

            update();
            this.countdownInterval = setInterval(update, 60000);
        }

        setupForm() {
            const form = document.getElementById('popupForm');
            if (!form) return;

            const phoneInput = form.querySelector('input[name="phone"]');
            if (phoneInput) {
                phoneInput.addEventListener('input', (e) => {
                    const value = e.target.value.replace(/[\s\-\(\)]/g, '');
                    if (value.length >= 9) {
                        e.target.classList.toggle('is-invalid', !validatePhone(value));
                        e.target.classList.toggle('is-valid', validatePhone(value));
                    } else {
                        e.target.classList.remove('is-valid', 'is-invalid');
                    }
                });
            }

            form.addEventListener('submit', (e) => {
                e.preventDefault();
                if (!this.isSubmitting) {
                    this.handleSubmit(form);
                }
            });
        }

        async handleSubmit(form) {
            if (!form.checkValidity()) {
                form.classList.add('was-validated');
                return;
            }

            const formData = new FormData(form);
            const name = formData.get('name')?.trim();
            const phone = formData.get('phone')?.replace(/[\s\-\(\)]/g, '');
            const offerId = formData.get('offer_id');

            if (!name) {
                this.showError(this.isEnglish ? 'Please enter your name' : 'الرجاء إدخال اسمك');
                return;
            }

            if (!validatePhone(phone)) {
                this.showError(this.isEnglish ? 'Please enter a valid phone number' : 'الرجاء إدخال رقم هاتف صحيح');
                return;
            }

            const submitBtn = document.getElementById('submitBtn');
            const originalText = submitBtn?.innerHTML;
            const loadingText = this.isEnglish ? 'Registering...' : 'جاري التسجيل...';

            this.isSubmitting = true;
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = `<i class="fa fa-spinner fa-spin me-2"></i>${loadingText}`;
            }

            try {
                // ✅ استخدام jsonRpc المحدث مع دعم CSRF
                const result = await this.jsonRpc('/popup/submit', {
                    name: name,
                    phone: phone,
                    offer_id: offerId ? parseInt(offerId) : null
                });

                if (result?.success) {
                    this.handleSuccess(name);
                } else {
                    this.showError(result?.error || (this.isEnglish ? 'An error occurred' : 'حدث خطأ'));
                    this.resetButton(submitBtn, originalText);
                }

            } catch (error) {
                log('Error:', error);
                this.showError(this.isEnglish ? 'Connection error' : 'خطأ في الاتصال');
                this.resetButton(submitBtn, originalText);
            }

            this.isSubmitting = false;
        }

        handleSuccess(name) {
            log('Submission successful');

            const form = document.getElementById('popupForm');
            const formContainer = document.getElementById('formContainer');
            const successDiv = document.getElementById('popupSuccess');
            const successName = document.getElementById('successName');
            const successMessage = document.getElementById('successMessage');

            if (form) form.style.display = 'none';
            if (formContainer) formContainer.style.display = 'none';

            if (successName) successName.textContent = name;

            if (successMessage && this.settings.success_message) {
                successMessage.textContent = this.settings.success_message.replace('{name}', name);
            }

            if (successDiv) successDiv.style.display = 'block';

            const duration = this.settings?.cookie_duration || 7;
            setCookie(CONFIG.COOKIE_NAME, 'true', duration);
            log(`Cookie set for ${duration} days`);
        }

        showError(message) {
            if (typeof window.AlomranRegistration !== 'undefined' &&
                typeof window.AlomranRegistration.showToast === 'function') {
                window.AlomranRegistration.showToast(message, 'error');
            } else {
                this.showCustomToast(message, 'error');
            }
        }

        showCustomToast(message, type = 'info') {
            const existingToast = document.getElementById('popupToast');
            if (existingToast) existingToast.remove();

            const toast = document.createElement('div');
            toast.id = 'popupToast';
            toast.className = `alert alert-${type === 'error' ? 'danger' : 'success'} position-fixed`;
            toast.style.cssText = `
                top: 20px;
                ${this.isRtl ? 'left' : 'right'}: 20px;
                z-index: 99999;
                min-width: 300px;
                animation: slideIn 0.3s ease-out;
            `;
            toast.innerHTML = `
                <i class="fa fa-${type === 'error' ? 'exclamation-circle' : 'check-circle'} me-2"></i>
                ${message}
            `;
            document.body.appendChild(toast);

            setTimeout(() => toast.remove(), 5000);
        }

        resetButton(btn, originalText) {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        }

        scheduleDisplay() {
            const delay = (this.settings?.delay_seconds || 3) * 1000;

            if (this.settings?.show_on_mobile === false && window.innerWidth < 768) {
                log('Popup disabled on mobile');
                return;
            }

            log(`Scheduling popup display in ${delay}ms`);

            setTimeout(() => {
                this.showPopup();
            }, delay);
        }

        showPopup() {
            log('Showing popup');

            const popupElement = document.getElementById('offerPopup');
            if (!popupElement) return;

            try {
                if (typeof bootstrap !== 'undefined') {
                    new bootstrap.Modal(popupElement).show();
                } else if (typeof $ !== 'undefined' && $.fn?.modal) {
                    $(popupElement).modal('show');
                } else {
                    popupElement.style.display = 'block';
                    popupElement.classList.add('show');
                    document.body.classList.add('modal-open');

                    const backdrop = document.createElement('div');
                    backdrop.className = 'modal-backdrop fade show';
                    backdrop.id = 'popup-backdrop';
                    document.body.appendChild(backdrop);
                }
            } catch (error) {
                log('Error showing popup:', error);
            }
        }

        hidePopup() {
            const popupElement = document.getElementById('offerPopup');
            if (!popupElement) return;

            try {
                if (typeof bootstrap !== 'undefined') {
                    bootstrap.Modal.getInstance(popupElement)?.hide();
                } else if (typeof $ !== 'undefined' && $.fn?.modal) {
                    $(popupElement).modal('hide');
                } else {
                    popupElement.style.display = 'none';
                    popupElement.classList.remove('show');
                    document.body.classList.remove('modal-open');
                    document.getElementById('popup-backdrop')?.remove();
                }
            } catch (error) {
                log('Error hiding popup:', error);
            }
        }

        setupCloseHandlers() {
            const popupElement = document.getElementById('offerPopup');
            if (!popupElement) return;

            const closeBtn = popupElement.querySelector('[data-bs-dismiss="modal"]');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    setCookie(CONFIG.COOKIE_NAME, 'dismissed', 1);
                });
            }

            const cleanup = () => {
                if (this.countdownInterval) {
                    clearInterval(this.countdownInterval);
                }
            };

            if (typeof $ !== 'undefined' && $.fn?.modal) {
                $(popupElement).on('hidden.bs.modal', cleanup);
            } else {
                popupElement.addEventListener('hidden.bs.modal', cleanup);
            }
        }

        setupExitIntent() {
            log('Exit intent enabled');

            document.addEventListener('mouseleave', (e) => {
                if (e.clientY < 0 && !this.exitIntentShown && !getCookie(CONFIG.COOKIE_NAME)) {
                    this.exitIntentShown = true;
                    log('Exit intent triggered');
                    this.showPopup();
                }
            });
        }
    }

    // ============================================================
    // INITIALIZE
    // ============================================================

    window.AlomranPopup = new PopupHandler();

})();