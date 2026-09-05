/** @odoo-module **/

(function() {
    'use strict';

    console.log('=== UNIVERSAL COURSE REGISTRATION JS LOADED ===');

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCourseRegistration);
    } else {
        initCourseRegistration();
    }

    function initCourseRegistration() {
        console.log('🎓 Initializing Course Registration System');

        // Find all registration buttons (flexible selector)
        const registerButtons = document.querySelectorAll(
            '.btn-register, .btn-register-lang, [data-action="register"]'
        );

        if (registerButtons.length === 0) {
            console.log('ℹ️ No registration buttons found on this page');
            return;
        }

        console.log(`✅ Found ${registerButtons.length} registration buttons`);

        // Find modal (try multiple IDs)
        const modalElement = document.getElementById('registrationModal')
                          || document.getElementById('registrationModalLang')
                          || document.querySelector('.modal[id*="registration"]');

        if (!modalElement) {
            console.error('❌ No registration modal found');
            return;
        }

        console.log('✅ Modal found:', modalElement.id);

        // Find form
        const form = document.getElementById('courseRegistrationForm')
                  || document.getElementById('courseRegistrationFormLang')
                  || modalElement.querySelector('form');

        if (!form) {
            console.error('❌ No registration form found');
            return;
        }

        console.log('✅ Form found:', form.id);

        // Check jQuery
        if (typeof $ === 'undefined') {
            console.error('❌ jQuery not loaded');
            return;
        }

        console.log('✅ jQuery available');

        // Setup buttons
        setupRegistrationButtons(registerButtons, modalElement);

        // Setup form
        setupRegistrationForm(form, modalElement);

        console.log('🎉 Course registration system fully initialized');
    }

    function setupRegistrationButtons(buttons, modal) {
        buttons.forEach((button, index) => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                console.log(`🔘 Registration button ${index + 1} clicked`);

                const courseName = this.getAttribute('data-course');
                const coursePrice = this.getAttribute('data-price');

                console.log('📚 Course:', courseName);
                console.log('💰 Price:', coursePrice);

                // Find modal elements (flexible selectors)
                const nameElement = modal.querySelector('[id*="modalCourseName"]');
                const priceElement = modal.querySelector('[id*="modalCoursePrice"]');
                const hiddenNameInput = modal.querySelector('input[id*="courseName"]');
                const hiddenPriceInput = modal.querySelector('input[id*="coursePrice"]');

                // Populate modal
                if (nameElement) nameElement.textContent = courseName;
                if (priceElement) priceElement.textContent = coursePrice;
                if (hiddenNameInput) hiddenNameInput.value = courseName;
                if (hiddenPriceInput) hiddenPriceInput.value = coursePrice;

                // Show modal with jQuery
                try {
                    $(modal).modal('show');
                    console.log('✅ Modal shown');
                } catch (error) {
                    console.error('❌ Error showing modal:', error);
                }
            });
        });

        console.log(`✅ ${buttons.length} buttons configured`);
    }

    /**
     * ✅ Odoo-compatible JSON-RPC call with CSRF support
     */
    async function jsonRpc(url, params) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',  // ✅ مهم جداً للـ CSRF!
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: params,
                id: Math.floor(Math.random() * 1000000000)
            })
        });

        const data = await response.json();

        if (data.error) {
            console.error('RPC Error:', data.error);
            throw new Error(data.error.message || data.error.data?.message || 'RPC Error');
        }

        return data.result;
    }

    function setupRegistrationForm(form, modal) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('📤 Form submitted');

            const formData = new FormData(form);
            const name = formData.get('name');
            const phone = formData.get('phone');
            const email = formData.get('email');
            const courseName = formData.get('course_name');
            const coursePrice = formData.get('course_price');

            console.log('📋 Form data:', {name, phone, email, courseName, coursePrice});

            // Validate
            if (!name || !phone) {
                alert('Please fill in all required fields.');
                return;
            }

            // Find submit button
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Submitting...';

            try {
                // Detect endpoint from current page URL
                const currentPath = window.location.pathname;
                let endpoint = '/course/register'; // default

                if (currentPath.includes('teachers')) {
                    endpoint = '/teachers/register';
                    console.log('📍 Using Teachers endpoint');
                } else if (currentPath.includes('languages')) {
                    endpoint = '/languages/register';
                    console.log('📍 Using Languages endpoint');
                } else if (currentPath.includes('it-programs')) {
                    endpoint = '/it-programs/register';
                    console.log('📍 Using IT Programs endpoint');
                } else {
                    console.log('📍 Using default endpoint');
                }

                console.log('🌐 Sending to:', endpoint);

                // ✅ استخدام jsonRpc مع CSRF support
                const result = await jsonRpc(endpoint, {
                    name: name,
                    phone: phone,
                    email: email,
                    course_name: courseName,
                    course_price: coursePrice
                });

                console.log('📊 Response data:', result);

                if (result && result.success) {
                    console.log('✅ Registration successful!');

                    // Find form and success containers (flexible)
                    const formContainer = modal.querySelector('[id*="registrationForm"]');
                    const successContainer = modal.querySelector('[id*="registrationSuccess"]');

                    if (formContainer) {
                        formContainer.style.display = 'none';
                        console.log('✅ Form hidden');
                    }

                    if (successContainer) {
                        successContainer.style.display = 'block';
                        console.log('✅ Success message shown');
                    }

                    form.reset();

                } else {
                    console.error('❌ Registration failed:', result);
                    alert(result?.error || 'An error occurred. Please try again.');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }

            } catch (error) {
                console.error('❌ Error:', error);
                alert('Connection error. Please try again.');
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });

        console.log('✅ Form submission handler configured');

        // Reset on modal close
        $(modal).on('hidden.bs.modal', function() {
            console.log('🔄 Modal closed - resetting');

            const formContainer = modal.querySelector('[id*="registrationForm"]');
            const successContainer = modal.querySelector('[id*="registrationSuccess"]');

            if (formContainer) formContainer.style.display = 'block';
            if (successContainer) successContainer.style.display = 'none';

            form.reset();

            // Reset submit button
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = false;
            }
        });

        console.log('✅ Modal close handler configured');
    }

})();