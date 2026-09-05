/** @odoo-module **/

// Counter animation for statistics
document.addEventListener('DOMContentLoaded', function() {

    // Counter animation
    const counterElements = document.querySelectorAll('.counter-number');

    if (counterElements.length > 0) {
        const animateCounter = (element) => {
            const target = parseInt(element.textContent);
            const duration = 2000; // 2 seconds
            const increment = target / (duration / 16); // 60fps
            let current = 0;

            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    element.textContent = target;
                    clearInterval(timer);
                } else {
                    element.textContent = Math.ceil(current);
                }
            }, 16);
        };

        // Intersection Observer for counter animation on scroll
        const observerOptions = {
            threshold: 0.5,
            rootMargin: '0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !entry.target.classList.contains('animated')) {
                    entry.target.classList.add('animated');
                    animateCounter(entry.target);
                }
            });
        }, observerOptions);

        counterElements.forEach(element => {
            observer.observe(element);
        });
    }

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.length > 1) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // Add animation classes on scroll
    const animateOnScroll = () => {
        const elements = document.querySelectorAll('.o_animate:not(.o_visible)');

        elements.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;

            if (elementTop < windowHeight * 0.85) {
                element.classList.add('o_visible');
            }
        });
    };

    // Run on scroll
    window.addEventListener('scroll', animateOnScroll);

    // Run once on load
    animateOnScroll();

    // Newsletter form handling
    const newsletterForm = document.querySelector('.js_subscribe_btn');
    if (newsletterForm) {
        newsletterForm.addEventListener('click', function(e) {
            e.preventDefault();
            const emailInput = document.querySelector('.js_subscribe_value');
            const email = emailInput.value;

            // Basic email validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

            if (emailRegex.test(email)) {
                // Show success message
                const subscribeWrap = document.querySelector('.js_subscribe_wrap');
                const subscribedWrap = document.querySelector('.js_subscribed_wrap');

                if (subscribeWrap && subscribedWrap) {
                    subscribeWrap.classList.add('d-none');
                    subscribedWrap.classList.remove('d-none');

                    // Reset after 5 seconds
                    setTimeout(() => {
                        subscribeWrap.classList.remove('d-none');
                        subscribedWrap.classList.add('d-none');
                        emailInput.value = '';
                    }, 5000);
                }
            } else {
                // Show error
                emailInput.classList.add('is-invalid');
                setTimeout(() => {
                    emailInput.classList.remove('is-invalid');
                }, 3000);
            }
        });
    }

    // Back to top button
    const createBackToTopButton = () => {
        const button = document.createElement('button');
        button.innerHTML = '<i class="fa fa-arrow-up"></i>';
        button.className = 'back-to-top';
        button.style.cssText = `
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: #1e88e5;
            color: white;
            border: none;
            cursor: pointer;
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(30, 136, 229, 0.4);
            transition: all 0.3s ease;
        `;

        button.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });

        window.addEventListener('scroll', () => {
            if (window.pageYOffset > 300) {
                button.style.display = 'flex';
            } else {
                button.style.display = 'none';
            }
        });

        document.body.appendChild(button);
    };

    createBackToTopButton();

});
