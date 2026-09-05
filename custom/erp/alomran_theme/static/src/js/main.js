/** @odoo-module **/

/**
 * Alomran Theme - Main JavaScript
 * ================================
 * Core functionality for the website.
 *
 * Improvements:
 * - Throttled scroll events
 * - Intersection Observer for animations
 * - Reduced motion support
 * - No console.log in production
 */

(function() {
    'use strict';

    // ============================================================
    // CONFIGURATION
    // ============================================================

    const CONFIG = {
        DEBUG: false,
        SCROLL_THROTTLE_MS: 100,
        ANIMATION_THRESHOLD: 0.1
    };

    // ============================================================
    // UTILITY FUNCTIONS
    // ============================================================

    function log(...args) {
        if (CONFIG.DEBUG) {
            console.log('[AlomranMain]', ...args);
        }
    }

    /**
     * Throttle function to limit execution rate
     */
    function throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * Check if user prefers reduced motion
     */
    function prefersReducedMotion() {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    // ============================================================
    // MAIN CLASS
    // ============================================================

    class AlomranMain {
        constructor() {
            this.observers = [];
            this.init();
        }

        init() {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.setup());
            } else {
                this.setup();
            }
        }

        setup() {
            log('Setting up main functionality');

            this.setupSmoothScroll();
            this.setupNavbarScroll();
            this.setupBackToTop();
            this.setupAnimations();
            this.setupLazyLoad();
            this.setupFormValidation();
            this.setupStatsCounter();

            log('Main functionality initialized');
        }

        // ============================================================
        // SMOOTH SCROLL
        // ============================================================

        setupSmoothScroll() {
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', (e) => {
                    const href = anchor.getAttribute('href');
                    if (href === '#' || href === '#!') return;

                    e.preventDefault();
                    const target = document.querySelector(href);

                    if (target) {
                        target.scrollIntoView({
                            behavior: prefersReducedMotion() ? 'auto' : 'smooth',
                            block: 'start'
                        });
                    }
                });
            });
        }

        // ============================================================
        // NAVBAR SCROLL EFFECT
        // ============================================================

        setupNavbarScroll() {
            const navbar = document.querySelector('.navbar, #mainNavbar');
            if (!navbar) return;

            const handleScroll = throttle(() => {
                if (window.scrollY > 50) {
                    navbar.classList.add('scrolled');
                } else {
                    navbar.classList.remove('scrolled');
                }
            }, CONFIG.SCROLL_THROTTLE_MS);

            window.addEventListener('scroll', handleScroll, { passive: true });

            // Initial check
            handleScroll();
        }

        // ============================================================
        // BACK TO TOP BUTTON
        // ============================================================

        setupBackToTop() {
            const btn = document.getElementById('btn-back-to-top');
            if (!btn) return;

            const handleScroll = throttle(() => {
                btn.style.display = window.scrollY > 300 ? 'block' : 'none';
            }, CONFIG.SCROLL_THROTTLE_MS);

            window.addEventListener('scroll', handleScroll, { passive: true });

            btn.addEventListener('click', () => {
                window.scrollTo({
                    top: 0,
                    behavior: prefersReducedMotion() ? 'auto' : 'smooth'
                });
            });

            // Initial check
            handleScroll();
        }

        // ============================================================
        // ANIMATIONS (with Intersection Observer)
        // ============================================================

        setupAnimations() {
            if (prefersReducedMotion()) {
                log('Reduced motion preferred - skipping animations');
                // Just make elements visible
                document.querySelectorAll('.animate-scale, .animate-float').forEach(el => {
                    el.style.opacity = '1';
                    el.style.transform = 'none';
                });
                return;
            }

            if (!('IntersectionObserver' in window)) {
                log('IntersectionObserver not supported');
                return;
            }

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'scale(1) translateY(0)';
                        observer.unobserve(entry.target);
                    }
                });
            }, {
                threshold: CONFIG.ANIMATION_THRESHOLD,
                rootMargin: '0px 0px -50px 0px'
            });

            document.querySelectorAll('.animate-scale, .animate-float, .animate-fade-in').forEach(el => {
                el.style.opacity = '0';
                el.style.transform = 'scale(0.95) translateY(20px)';
                el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                observer.observe(el);
            });

            this.observers.push(observer);
        }

        // ============================================================
        // LAZY LOAD IMAGES
        // ============================================================

        setupLazyLoad() {
            if (!('IntersectionObserver' in window)) return;

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            img.classList.add('loaded');
                        }
                        observer.unobserve(img);
                    }
                });
            }, {
                rootMargin: '50px 0px'
            });

            document.querySelectorAll('img[data-src]').forEach(img => {
                observer.observe(img);
            });

            this.observers.push(observer);
        }

        // ============================================================
        // FORM VALIDATION
        // ============================================================

        setupFormValidation() {
            document.querySelectorAll('.needs-validation').forEach(form => {
                form.addEventListener('submit', (e) => {
                    if (!form.checkValidity()) {
                        e.preventDefault();
                        e.stopPropagation();
                    }
                    form.classList.add('was-validated');
                }, false);
            });
        }

        // ============================================================
        // STATS COUNTER ANIMATION
        // ============================================================

        setupStatsCounter() {
            if (prefersReducedMotion()) {
                log('Reduced motion - skipping counter animation');
                return;
            }

            if (!('IntersectionObserver' in window)) return;

            const statElements = document.querySelectorAll('.stat-card h3, .stat-number, [data-count]');
            if (!statElements.length) return;

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.animateCounter(entry.target);
                        observer.unobserve(entry.target);
                    }
                });
            }, {
                threshold: 0.5
            });

            statElements.forEach(el => observer.observe(el));
            this.observers.push(observer);
        }

        animateCounter(element) {
            const text = element.textContent.trim();

            // Extract number from text (handles "10,000+", "50+", "14+", etc.)
            const match = text.match(/[\d,]+/);
            if (!match) return;

            const targetNumber = parseInt(match[0].replace(/,/g, ''));
            if (isNaN(targetNumber)) return;

            // Get prefix and suffix
            const prefix = text.substring(0, text.indexOf(match[0]));
            const suffix = text.substring(text.indexOf(match[0]) + match[0].length);

            // Animate
            const duration = 2000;
            const startTime = performance.now();

            const animate = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);

                // Ease out cubic
                const easeProgress = 1 - Math.pow(1 - progress, 3);
                const currentNumber = Math.floor(easeProgress * targetNumber);

                element.textContent = prefix + currentNumber.toLocaleString() + suffix;

                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    element.textContent = text; // Restore original text
                }
            };

            requestAnimationFrame(animate);
        }

        // ============================================================
        // CLEANUP
        // ============================================================

        destroy() {
            this.observers.forEach(observer => observer.disconnect());
            this.observers = [];
        }
    }

    // ============================================================
    // INITIALIZE
    // ============================================================

    window.AlomranMain = new AlomranMain();

})();
