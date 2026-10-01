/**
 * NAVIER YACHTS Website Main JavaScript
 * Mobile navigation, hero slider, product tabs, image loading states.
 *
 * The hero slider lives here as a single implementation. An earlier duplicate
 * implementation in this file targeted a ".slider-dot" element that does not
 * exist in the markup and threw a TypeError every 5 seconds.
 */

document.addEventListener('DOMContentLoaded', function () {

    /* -------------------------------------------------------------- *
     * Mobile menu
     * -------------------------------------------------------------- */
    const menuToggle = document.querySelector('.menu-toggle');
    const navMenu = document.querySelector('.nav-menu');

    if (menuToggle && navMenu) {
        menuToggle.addEventListener('click', function () {
            const isOpen = navMenu.classList.toggle('active');
            menuToggle.classList.toggle('active', isOpen);
            menuToggle.setAttribute('aria-expanded', String(isOpen));
        });

        // Close the menu when a link is followed.
        navMenu.addEventListener('click', function (event) {
            if (event.target.closest('a')) {
                navMenu.classList.remove('active');
                menuToggle.classList.remove('active');
                menuToggle.setAttribute('aria-expanded', 'false');
            }
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && navMenu.classList.contains('active')) {
                navMenu.classList.remove('active');
                menuToggle.classList.remove('active');
                menuToggle.setAttribute('aria-expanded', 'false');
                menuToggle.focus();
            }
        });
    }

    /* -------------------------------------------------------------- *
     * Hero slider
     * -------------------------------------------------------------- */
    const heroSection = document.querySelector('.hero');
    const heroSlides = document.querySelectorAll('.hero-slide');
    const indicators = document.querySelectorAll('.indicator');
    const prevBtn = document.querySelector('.prev-slide');
    const nextBtn = document.querySelector('.next-slide');

    if (heroSection && heroSlides.length > 1) {
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
        const SLIDE_MS = 6000;
        let currentSlide = 0;
        let slideTimer = null;
        let paused = false;

        function showSlide(index) {
            const total = heroSlides.length;
            const next = ((index % total) + total) % total;

            heroSlides.forEach(function (slide, i) {
                const isActive = i === next;
                slide.classList.toggle('active', isActive);
                slide.setAttribute('aria-hidden', String(!isActive));
            });

            indicators.forEach(function (indicator, i) {
                const isActive = i === next;
                indicator.classList.toggle('active', isActive);
                indicator.setAttribute('aria-selected', String(isActive));
                indicator.setAttribute('tabindex', isActive ? '0' : '-1');
            });

            currentSlide = next;
        }

        function stopAutoSlide() {
            if (slideTimer) {
                clearInterval(slideTimer);
                slideTimer = null;
            }
        }

        function startAutoSlide() {
            stopAutoSlide();
            if (paused || reduceMotion.matches || document.hidden) return;
            slideTimer = setInterval(function () {
                showSlide(currentSlide + 1);
            }, SLIDE_MS);
        }

        function goTo(index) {
            showSlide(index);
            startAutoSlide();
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', function () { goTo(currentSlide + 1); });
        }
        if (prevBtn) {
            prevBtn.addEventListener('click', function () { goTo(currentSlide - 1); });
        }

        indicators.forEach(function (indicator, index) {
            indicator.addEventListener('click', function () { goTo(index); });
            indicator.addEventListener('keydown', function (event) {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    goTo(index);
                }
            });
        });

        // Keyboard navigation while the slider has focus.
        heroSection.addEventListener('keydown', function (event) {
            if (event.key === 'ArrowRight') { goTo(currentSlide + 1); }
            if (event.key === 'ArrowLeft') { goTo(currentSlide - 1); }
        });

        // Pause while the pointer or focus is inside the slider.
        heroSection.addEventListener('mouseenter', function () { paused = true; stopAutoSlide(); });
        heroSection.addEventListener('mouseleave', function () { paused = false; startAutoSlide(); });
        heroSection.addEventListener('focusin', function () { paused = true; stopAutoSlide(); });
        heroSection.addEventListener('focusout', function () { paused = false; startAutoSlide(); });

        // Do not animate in a background tab.
        document.addEventListener('visibilitychange', function () {
            if (document.hidden) { stopAutoSlide(); } else { startAutoSlide(); }
        });

        // React if the user changes their motion preference mid-session.
        if (typeof reduceMotion.addEventListener === 'function') {
            reduceMotion.addEventListener('change', startAutoSlide);
        }

        showSlide(0);
        startAutoSlide();
    }

    /* -------------------------------------------------------------- *
     * Product tabs (products page)
     * -------------------------------------------------------------- */
    const productTabs = document.querySelectorAll('.product-tabs a');

    productTabs.forEach(function (tab) {
        tab.addEventListener('click', function (e) {
            const targetId = tab.getAttribute('href');
            if (!targetId || targetId.charAt(0) !== '#') return;

            const targetSection = document.querySelector(targetId);
            if (!targetSection) return;

            e.preventDefault();

            productTabs.forEach(function (t) { t.classList.remove('active'); });
            tab.classList.add('active');

            const header = document.querySelector('header');
            const headerHeight = header ? header.offsetHeight : 0;
            const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

            window.scrollTo({
                top: targetSection.offsetTop - headerHeight - 20,
                behavior: reduceMotion ? 'auto' : 'smooth'
            });

            if (history.replaceState) history.replaceState(null, '', targetId);
        });
    });

    /* -------------------------------------------------------------- *
     * Image load / error states
     * -------------------------------------------------------------- */
    const allImages = document.querySelectorAll('img:not(.footer-logo)');

    allImages.forEach(function (img) {
        if (img.complete) {
            img.classList.add('loaded');
            return;
        }

        img.classList.add('loading');

        img.addEventListener('load', function () {
            img.classList.remove('loading');
            img.classList.add('loaded');
        });

        img.addEventListener('error', function () {
            img.classList.remove('loading');
            img.classList.add('error');
        });
    });

    /* -------------------------------------------------------------- *
     * Footer: current year and back-to-top
     * (The footer markup itself is static in the HTML so that crawlers
     *  and no-JS visitors see the full internal link graph.)
     * -------------------------------------------------------------- */
    const yearEl = document.querySelector('.footer-year');
    if (yearEl) {
        yearEl.textContent = String(new Date().getFullYear());
    }

    const backToTopButton = document.querySelector('.back-to-top');
    if (backToTopButton) {
        backToTopButton.addEventListener('click', function (event) {
            event.preventDefault();
            const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
        });

        const syncBackToTop = function () {
            backToTopButton.style.opacity = window.pageYOffset > 300 ? '1' : '0';
        };
        syncBackToTop();
        window.addEventListener('scroll', syncBackToTop, { passive: true });
    }

});
