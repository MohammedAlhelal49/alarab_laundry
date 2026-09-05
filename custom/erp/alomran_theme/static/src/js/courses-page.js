/** @odoo-module **/

(function() {
    'use strict';

    console.log('=== COURSES PAGE JS LOADED ===');

    // Only run on /courses page
    if (!window.location.pathname.includes('/courses')) {
        return;
    }

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCoursesPage);
    } else {
        initCoursesPage();
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

    function initCoursesPage() {
        console.log('🎓 Initializing Courses Page Registration');

        // Find all course cards
        const courseCards = document.querySelectorAll('.course-card');
        const modal = document.getElementById('registrationModalGeneral');
        const form = document.getElementById('courseRegistrationFormGeneral');

        if (!modal || !form) {
            console.log('ℹ️ General registration modal not found');
            return;
        }

        if (typeof $ === 'undefined') {
            console.error('❌ jQuery not loaded');
            return;
        }

        console.log(`✅ Found ${courseCards.length} course cards`);

        // Setup click handlers
        courseCards.forEach((card, index) => {
            const button = card.querySelector('a[href="#register"]');

            if (button) {
                const courseName = card.querySelector('h5').textContent.trim();

                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    console.log(`🔘 Register clicked for: ${courseName}`);

                    // Populate modal
                    const modalTitle = document.getElementById('modalCourseNameGeneral');
                    const hiddenInput = document.getElementById('courseNameGeneral');

                    if (modalTitle) modalTitle.textContent = courseName;
                    if (hiddenInput) hiddenInput.value = courseName;

                    // Show modal
                    $(modal).modal('show');
                });
            }
        });

        // Handle form submission
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('📤 Form submitted');

            const formData = new FormData(form);
            const name = formData.get('name')?.trim();
            const phone = formData.get('phone')?.trim();
            const email = formData.get('email')?.trim();
            const courseName = formData.get('course_name');

            // Validate
            if (!name || !phone) {
                alert('Please fill in all required fields.');
                return;
            }

            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Submitting...';

            try {
                // ✅ استخدام jsonRpc مع CSRF support
                const result = await jsonRpc('/course/register', {
                    name: name,
                    phone: phone,
                    email: email,
                    course_name: courseName
                });

                console.log('📊 Response:', result);

                if (result && result.success) {
                    console.log('✅ Registration successful');

                    const formContainer = document.getElementById('registrationFormGeneral');
                    const successContainer = document.getElementById('registrationSuccessGeneral');

                    if (formContainer) formContainer.style.display = 'none';
                    if (successContainer) successContainer.style.display = 'block';

                    form.reset();
                } else {
                    alert(result?.error || 'An error occurred. Please try again.');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }
            } catch (error) {
                console.error('❌ Error:', error);
                alert('A connection error occurred. Please try again.');
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });

        // Reset on close
        $(modal).on('hidden.bs.modal', function() {
            const formContainer = document.getElementById('registrationFormGeneral');
            const successContainer = document.getElementById('registrationSuccessGeneral');

            if (formContainer) formContainer.style.display = 'block';
            if (successContainer) successContainer.style.display = 'none';

            form.reset();

            // Reset submit button
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = false;
            }
        });

        console.log('🎉 Courses page registration initialized');
    }

})();