/**
 * NAVIER YACHTS Website Main JavaScript
 * Handles interactive elements, sliders, and responsive behavior
 */

document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const menuToggle = document.querySelector('.menu-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            menuToggle.classList.toggle('active');
        });
    }
    
    // Hero slider functionality
    const heroSlides = document.querySelectorAll('.hero-slide');
    const sliderDots = document.querySelectorAll('.slider-dot');
    const prevSlideBtn = document.querySelector('.prev-slide');
    const nextSlideBtn = document.querySelector('.next-slide');
    let currentSlide = 0;
    let slideInterval;
    
    // Function to show a specific slide
    function showSlide(index) {
        // Hide all slides
        heroSlides.forEach(slide => {
            slide.classList.remove('active');
        });
        
        // Remove active class from all dots
        sliderDots.forEach(dot => {
            dot.classList.remove('active');
        });
        
        // Show the current slide and activate corresponding dot
        heroSlides[index].classList.add('active');
        sliderDots[index].classList.add('active');
        
        currentSlide = index;
    }
    
    // Initialize automatic slider
    function startSlideInterval() {
        slideInterval = setInterval(() => {
            let nextIndex = (currentSlide + 1) % heroSlides.length;
            showSlide(nextIndex);
        }, 5000); // Change slide every 5 seconds
    }
    
    // Event listeners for slider controls
    if (prevSlideBtn) {
        prevSlideBtn.addEventListener('click', function() {
            clearInterval(slideInterval);
            let prevIndex = (currentSlide - 1 + heroSlides.length) % heroSlides.length;
            showSlide(prevIndex);
            startSlideInterval();
        });
    }
    
    if (nextSlideBtn) {
        nextSlideBtn.addEventListener('click', function() {
            clearInterval(slideInterval);
            let nextIndex = (currentSlide + 1) % heroSlides.length;
            showSlide(nextIndex);
            startSlideInterval();
        });
    }
    
    // Add click event to dots
    sliderDots.forEach((dot, index) => {
        dot.addEventListener('click', function() {
            clearInterval(slideInterval);
            showSlide(index);
            startSlideInterval();
        });
    });
    
    // Start the automatic slider
    if (heroSlides.length > 0) {
        startSlideInterval();
    }
    
    // Handle product tabs in products page
    const productTabs = document.querySelectorAll('.product-tabs a');
    
    productTabs.forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all tabs
            productTabs.forEach(t => {
                t.classList.remove('active');
            });
            
            // Add active class to current tab
            this.classList.add('active');
            
            // Scroll to the target section
            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            
            if (targetSection) {
                // Smooth scroll to target section with offset for fixed header
                const headerHeight = document.querySelector('header').offsetHeight;
                const targetPosition = targetSection.offsetTop - headerHeight - 20;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Testimonial slider
    const testimonialSlides = document.querySelectorAll('.testimonial-slide');
    let currentTestimonial = 0;
    let testimonialInterval;
    
    function showTestimonial(index) {
        testimonialSlides.forEach(slide => {
            slide.classList.remove('active');
        });
        
        testimonialSlides[index].classList.add('active');
        currentTestimonial = index;
    }
    
    // Initialize testimonial slider if testimonials exist
    if (testimonialSlides.length > 1) {
        testimonialInterval = setInterval(() => {
            let nextIndex = (currentTestimonial + 1) % testimonialSlides.length;
            showTestimonial(nextIndex);
        }, 7000); // Change testimonial every 7 seconds
    }
    
    // Image lazy loading and error handling
    const allImages = document.querySelectorAll('img:not(.footer-logo)');
    
    allImages.forEach(img => {
        // Add loading class
        img.classList.add('loading');
        
        img.addEventListener('load', function() {
            // Replace loading class with loaded
