/**
 * AL OMRAN TRAINING CENTER - Interactive Animations
 * مركز العمران للتدريب والتطوير - الحركات التفاعلية
 * Version: 2.0
 */

(function() {
    'use strict';

    // ============================================================
    // CONFIGURATION
    // ============================================================
    const CONFIG = {
        REVEAL_THRESHOLD: 0.15,
        REVEAL_ROOT_MARGIN: '0px 0px -50px 0px',
        COUNTER_DURATION: 2000,
        COUNTER_THRESHOLD: 0.5,
        NAVBAR_SCROLL_OFFSET: 50,
        SCROLL_THROTTLE: 100,
        PARALLAX_SPEED: 0.5,
        DEBUG: false
    };

    // ============================================================
    // UTILITY FUNCTIONS
    // ============================================================
    
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

    function prefersReducedMotion() {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    function log(...args) {
        if (CONFIG.DEBUG) {
            console.log('[AlOmran]', ...args);
        }
    }

    // ============================================================
    // SCROLL REVEAL ANIMATIONS
    // ============================================================
    
    class ScrollReveal {
        constructor() {
            this.elements = [];
            this.observer = null;
            this.init();
        }

        init() {
            if (prefersReducedMotion()) {
                document.querySelectorAll('.ao-reveal, .ao-reveal-up, .ao-reveal-down, .ao-reveal-left, .ao-reveal-right, .ao-reveal-scale').forEach(el => {
                    el.classList.add('ao-visible');
                });
                return;
            }

            if (!('IntersectionObserver' in window)) {
                log('IntersectionObserver not supported');
                return;
            }

            this.observer = new IntersectionObserver(
                (entries) => this.handleIntersect(entries),
                {
                    threshold: CONFIG.REVEAL_THRESHOLD,
                    rootMargin: CONFIG.REVEAL_ROOT_MARGIN
                }
            );

            this.observeElements();
        }

        observeElements() {
            const selectors = [
                '.ao-reveal',
                '.ao-reveal-up',
                '.ao-reveal-down',
                '.ao-reveal-left',
                '.ao-reveal-right',
                '.ao-reveal-scale',
                '[data-ao-animate]'
            ];

            document.querySelectorAll(selectors.join(', ')).forEach(el => {
                this.observer.observe(el);
                this.elements.push(el);
            });

            log(`Observing ${this.elements.length} elements for scroll reveal`);
        }

        handleIntersect(entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const el = entry.target;
                    const delay = el.dataset.aoDelay || 0;

                    setTimeout(() => {
                        el.classList.add('ao-visible', 'ao-animated');
                        
                        const animation = el.dataset.aoAnimate;
                        if (animation) {
                            el.classList.add(`ao-animate-${animation}`);
                        }
                    }, parseInt(delay));

                    this.observer.unobserve(el);
                }
            });
        }

        destroy() {
            if (this.observer) {
                this.observer.disconnect();
            }
        }
    }

    // ============================================================
    // COUNTER ANIMATION
    // ============================================================
    
    class CounterAnimation {
        constructor() {
            this.counters = [];
            this.observer = null;
            this.init();
        }

        init() {
            if (prefersReducedMotion()) return;

            if (!('IntersectionObserver' in window)) return;

            this.observer = new IntersectionObserver(
                (entries) => this.handleIntersect(entries),
                { threshold: CONFIG.COUNTER_THRESHOLD }
            );

            this.observeCounters();
        }

        observeCounters() {
            const selectors = [
                '.ao-counter',
                '.ao-stat-number',
                '[data-ao-counter]',
                '.stat-number'
            ];

            document.querySelectorAll(selectors.join(', ')).forEach(el => {
                if (!el.dataset.aoCounterDone) {
                    this.observer.observe(el);
                    this.counters.push(el);
                }
            });

            log(`Observing ${this.counters.length} counters`);
        }

        handleIntersect(entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateCounter(entry.target);
                    this.observer.unobserve(entry.target);
                }
            });
        }

        animateCounter(element) {
            const text = element.textContent.trim();
            const match = text.match(/[\d,]+/);
            
            if (!match) return;

            const targetNumber = parseInt(match[0].replace(/,/g, ''));
            if (isNaN(targetNumber)) return;

            const prefix = text.substring(0, text.indexOf(match[0]));
            const suffix = text.substring(text.indexOf(match[0]) + match[0].length);

            element.dataset.aoCounterDone = 'true';
            element.classList.add('ao-counting');

            const duration = CONFIG.COUNTER_DURATION;
            const startTime = performance.now();
            const startNumber = 0;

            const animate = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);

                const easeProgress = 1 - Math.pow(1 - progress, 3);
                const currentNumber = Math.floor(easeProgress * (targetNumber - startNumber) + startNumber);

                element.textContent = prefix + currentNumber.toLocaleString() + suffix;

                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    element.textContent = text;
                    element.classList.remove('ao-counting');
                }
            };

            requestAnimationFrame(animate);
        }

        destroy() {
            if (this.observer) {
                this.observer.disconnect();
            }
        }
    }

    // ============================================================
    // NAVBAR SCROLL EFFECT
    // ============================================================
    
    class NavbarScroll {
        constructor() {
            this.navbar = null;
            this.init();
        }

        init() {
            this.navbar = document.querySelector('.ao-navbar, #mainNavbar, .navbar');
            if (!this.navbar) return;

            this.handleScroll = throttle(() => this.updateNavbar(), CONFIG.SCROLL_THROTTLE);
            window.addEventListener('scroll', this.handleScroll, { passive: true });
            
            this.updateNavbar();
        }

        updateNavbar() {
            if (window.scrollY > CONFIG.NAVBAR_SCROLL_OFFSET) {
                this.navbar.classList.add('scrolled');
            } else {
                this.navbar.classList.remove('scrolled');
            }
        }

        destroy() {
            window.removeEventListener('scroll', this.handleScroll);
        }
    }

    // ============================================================
    // SMOOTH SCROLL
    // ============================================================
    
    class SmoothScroll {
        constructor() {
            this.init();
        }

        init() {
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', (e) => this.handleClick(e, anchor));
            });
        }

        handleClick(e, anchor) {
            const href = anchor.getAttribute('href');
            if (href === '#' || href === '#!') return;

            const target = document.querySelector(href);
            if (!target) return;

            e.preventDefault();

            const navbarHeight = document.querySelector('.ao-navbar, #mainNavbar, .navbar')?.offsetHeight || 0;
            const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navbarHeight - 20;

            window.scrollTo({
                top: targetPosition,
                behavior: prefersReducedMotion() ? 'auto' : 'smooth'
            });
        }
    }

    // ============================================================
    // PARALLAX EFFECT
    // ============================================================
    
    class ParallaxEffect {
        constructor() {
            this.elements = [];
            this.init();
        }

        init() {
            if (prefersReducedMotion()) return;

            this.elements = document.querySelectorAll('.ao-parallax, [data-ao-parallax]');
            if (!this.elements.length) return;

            this.handleScroll = throttle(() => this.updateParallax(), 16);
            window.addEventListener('scroll', this.handleScroll, { passive: true });
        }

        updateParallax() {
            const scrollY = window.pageYOffset;

            this.elements.forEach(el => {
                const speed = parseFloat(el.dataset.aoParallaxSpeed) || CONFIG.PARALLAX_SPEED;
                const offset = scrollY * speed;
                el.style.transform = `translateY(${offset}px)`;
            });
        }

        destroy() {
            window.removeEventListener('scroll', this.handleScroll);
        }
    }

    // ============================================================
    // TILT EFFECT (3D Card)
    // ============================================================
    
    class TiltEffect {
        constructor() {
            this.init();
        }

        init() {
            if (prefersReducedMotion()) return;

            document.querySelectorAll('.ao-tilt, [data-ao-tilt]').forEach(el => {
                el.addEventListener('mousemove', (e) => this.handleMouseMove(e, el));
                el.addEventListener('mouseleave', (e) => this.handleMouseLeave(e, el));
            });
        }

        handleMouseMove(e, el) {
            const rect = el.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = (y - centerY) / 10;
            const rotateY = (centerX - x) / 10;

            el.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
        }

        handleMouseLeave(e, el) {
            el.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale(1)';
        }
    }

    // ============================================================
    // STAGGER ANIMATION
    // ============================================================
    
    class StaggerAnimation {
        constructor() {
            this.init();
        }

        init() {
            if (prefersReducedMotion()) return;

            const observer = new IntersectionObserver(
                (entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            this.animateChildren(entry.target);
                            observer.unobserve(entry.target);
                        }
                    });
                },
                { threshold: 0.1 }
            );

            document.querySelectorAll('.ao-stagger, [data-ao-stagger]').forEach(el => {
                observer.observe(el);
            });
        }

        animateChildren(parent) {
            const children = parent.children;
            const delay = parseInt(parent.dataset.aoStaggerDelay) || 100;
            const animation = parent.dataset.aoStaggerAnimation || 'fadeInUp';

            Array.from(children).forEach((child, index) => {
                child.style.opacity = '0';
                setTimeout(() => {
                    child.style.opacity = '1';
                    child.classList.add(`ao-animate-${animation}`);
                }, index * delay);
            });
        }
    }

    // ============================================================
    // LAZY LOAD IMAGES
    // ============================================================
    
    class LazyLoad {
        constructor() {
            this.init();
        }

        init() {
            if (!('IntersectionObserver' in window)) {
                document.querySelectorAll('img[data-src]').forEach(img => {
                    img.src = img.dataset.src;
                });
                return;
            }

            const observer = new IntersectionObserver(
                (entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            img.classList.add('ao-loaded');
                            observer.unobserve(img);
                        }
                    });
                },
                { rootMargin: '50px 0px' }
            );

            document.querySelectorAll('img[data-src]').forEach(img => {
                observer.observe(img);
            });
        }
    }

    // ============================================================
    // BACK TO TOP BUTTON
    // ============================================================
    
    class BackToTop {
        constructor() {
            this.button = null;
            this.init();
        }

        init() {
            this.button = document.querySelector('.ao-back-to-top, #backToTop');
            if (!this.button) return;

            this.handleScroll = throttle(() => this.updateVisibility(), CONFIG.SCROLL_THROTTLE);
            window.addEventListener('scroll', this.handleScroll, { passive: true });
            
            this.button.addEventListener('click', (e) => {
                e.preventDefault();
                window.scrollTo({
                    top: 0,
                    behavior: prefersReducedMotion() ? 'auto' : 'smooth'
                });
            });

            this.updateVisibility();
        }

        updateVisibility() {
            if (window.scrollY > 300) {
                this.button.classList.add('ao-visible');
                this.button.style.opacity = '1';
                this.button.style.visibility = 'visible';
            } else {
                this.button.classList.remove('ao-visible');
                this.button.style.opacity = '0';
                this.button.style.visibility = 'hidden';
            }
        }

        destroy() {
            window.removeEventListener('scroll', this.handleScroll);
        }
    }

    // ============================================================
    // FLOATING BUTTONS PULSE
    // ============================================================
    
    class FloatingButtons {
        constructor() {
            this.init();
        }

        init() {
            const buttons = document.querySelectorAll('.ao-floating-btn, .o_floating_btn');
            
            buttons.forEach(btn => {
                // Add pulse animation
                btn.classList.add('ao-animate-pulseSoft');
                
                // Stop pulse on hover
                btn.addEventListener('mouseenter', () => {
                    btn.classList.remove('ao-animate-pulseSoft');
                });
                
                btn.addEventListener('mouseleave', () => {
                    btn.classList.add('ao-animate-pulseSoft');
                });
            });
        }
    }

    // ============================================================
    // FORM ANIMATIONS
    // ============================================================
    
    class FormAnimations {
        constructor() {
            this.init();
        }

        init() {
            // Input focus animations
            document.querySelectorAll('.ao-input, .form-control').forEach(input => {
                input.addEventListener('focus', () => {
                    input.parentElement?.classList.add('ao-input-focused');
                });
                
                input.addEventListener('blur', () => {
                    input.parentElement?.classList.remove('ao-input-focused');
                });
            });

            // Form submit animation
          document.querySelectorAll('#contact_form_custom').forEach(form => {
                form.addEventListener('submit', () => {
                    const submitBtn = form.querySelector('button[type="submit"]');
                    if (!submitBtn) return;

                    submitBtn.classList.add('ao-loading');
                    submitBtn.disabled = true;
                });
            });
        }
    }

    // ============================================================
    // HOVER CARD EFFECTS
    // ============================================================
    
    class HoverCards {
        constructor() {
            this.init();
        }

        init() {
            if (prefersReducedMotion()) return;

            document.querySelectorAll('.ao-card, .ao-program-card, .ao-feature-box, .modern-card, .course-card').forEach(card => {
                card.addEventListener('mouseenter', () => {
                    card.style.transform = 'translateY(-10px)';
                });
                
                card.addEventListener('mouseleave', () => {
                    card.style.transform = 'translateY(0)';
                });
            });
        }
    }

    // ============================================================
    // TEXT REVEAL ANIMATION
    // ============================================================
    
    class TextReveal {
        constructor() {
            this.init();
        }

        init() {
            if (prefersReducedMotion()) return;

            document.querySelectorAll('[data-ao-text-reveal]').forEach(el => {
                const text = el.textContent;
                el.textContent = '';
                el.style.visibility = 'visible';

                // Split text into words
                const words = text.split(' ');
                words.forEach((word, index) => {
                    const span = document.createElement('span');
                    span.textContent = word + ' ';
                    span.style.opacity = '0';
                    span.style.display = 'inline-block';
                    span.style.transform = 'translateY(20px)';
                    span.style.transition = `opacity 0.5s ease ${index * 0.1}s, transform 0.5s ease ${index * 0.1}s`;
                    el.appendChild(span);
                });

                // Trigger animation when visible
                const observer = new IntersectionObserver((entries) => {
                    if (entries[0].isIntersecting) {
                        el.querySelectorAll('span').forEach(span => {
                            span.style.opacity = '1';
                            span.style.transform = 'translateY(0)';
                        });
                        observer.disconnect();
                    }
                }, { threshold: 0.5 });

                observer.observe(el);
            });
        }
    }

    // ============================================================
    // PROGRESS BAR ANIMATION
    // ============================================================
    
    class ProgressBarAnimation {
        constructor() {
            this.init();
        }

        init() {
            if (prefersReducedMotion()) return;

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const bar = entry.target;
                        const target = bar.dataset.aoProgress || bar.style.width || '100%';
                        bar.style.width = '0%';
                        
                        setTimeout(() => {
                            bar.style.transition = 'width 1.5s ease-out';
                            bar.style.width = target;
                        }, 100);

                        observer.unobserve(bar);
                    }
                });
            }, { threshold: 0.5 });

            document.querySelectorAll('.ao-progress-bar, [data-ao-progress]').forEach(bar => {
                observer.observe(bar);
            });
        }
    }

    // ============================================================
    // MAIN INITIALIZATION
    // ============================================================
    
    class AlOmranAnimations {
        constructor() {
            this.modules = {};
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
            log('Initializing Al Omran Animations...');

            // Initialize all modules
            this.modules.scrollReveal = new ScrollReveal();
            this.modules.counterAnimation = new CounterAnimation();
            this.modules.navbarScroll = new NavbarScroll();
            this.modules.smoothScroll = new SmoothScroll();
            this.modules.parallaxEffect = new ParallaxEffect();
            this.modules.tiltEffect = new TiltEffect();
            this.modules.staggerAnimation = new StaggerAnimation();
            this.modules.lazyLoad = new LazyLoad();
            this.modules.backToTop = new BackToTop();
            this.modules.floatingButtons = new FloatingButtons();
            this.modules.formAnimations = new FormAnimations();
            this.modules.hoverCards = new HoverCards();
            this.modules.textReveal = new TextReveal();
            this.modules.progressBar = new ProgressBarAnimation();

            log('All animation modules initialized');

            // Add loaded class to body
            document.body.classList.add('ao-animations-loaded');
        }

        destroy() {
            Object.values(this.modules).forEach(module => {
                if (module.destroy) {
                    module.destroy();
                }
            });
        }
    }

    // ============================================================
    // EXPORT & INITIALIZE
    // ============================================================
    
    // Initialize
    window.AlOmranAnimations = new AlOmranAnimations();

    // Expose for manual control
    window.AO = {
        refresh: function() {
            window.AlOmranAnimations.destroy();
            window.AlOmranAnimations = new AlOmranAnimations();
        },
        config: CONFIG
    };

})();
