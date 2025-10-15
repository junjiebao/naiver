/**
 * NAVIER YACHTS Footer Component
 * Dynamically inserts the footer content into all pages
 */

document.addEventListener('DOMContentLoaded', function() {
    // Insert footer content into all pages
    const footerElement = document.querySelector('footer');
    
    if (footerElement) {
        footerElement.innerHTML = `
        <div class="container">
            <!-- Footer Newsletter Section -->
            <div class="footer-newsletter">
            <div class="footer-newsletter-content">
                <div class="footer-newsletter-text">
                <h3>Subscribe to Our Newsletter</h3>
                <p>Stay updated with our latest news, boat launches, and maritime events.</p>
                </div>
                <div class="footer-newsletter-form">
                <form action="#" method="post">
                    <input type="email" name="email" placeholder="Enter your email address" required>
                    <button type="submit" class="submit-btn">Subscribe</button>
                </form>
                </div>
            </div>
            </div>
            
            <!-- Main Footer Content -->
            <div class="footer-content">
            <div class="footer-col">
                <img src="images/logo narrow.png" alt="NAVIER YACHTS" class="footer-logo">
                <p>NAVIER YACHTS FZCO bridges mass manufacturing excellence with Middle East regional demand, offering premium yachts and boats for GCC market.</p>
                <div class="social-links">
                <a href="#"><i class="fab fa-facebook-f"></i></a>
                <a href="#"><i class="fab fa-twitter"></i></a>
                <a href="#"><i class="fab fa-instagram"></i></a>
                <a href="#"><i class="fab fa-linkedin-in"></i></a>
                <a href="#"><i class="fab fa-youtube"></i></a>
                </div>
            </div>
            
            <div class="footer-col">
                <h4>Quick Links</h4>
                <ul>
                <li><a href="index.html">Home</a></li>
                <li><a href="about.html">About Us</a></li>
                <li><a href="products.html">Products & Services</a></li>
                <li><a href="projects.html">Projects</a></li>
                <li><a href="news.html">News & Events</a></li>
                <li><a href="contact.html">Contact Us</a></li>
                </ul>
            </div>
            
            <div class="footer-col">
                <h4>Our Products</h4>
                <ul>
                <li><a href="products.html#tidemaster">TideMaster Boats</a></li>
                <li><a href="products.html#Patrol">SnakeHead Patrol Boats</a></li>
                <li><a href="products.html#imported">Imported Yachts</a></li>
                <li><a href="products.html#consultancy">Yacht Consultancy</a></li>
                <li><a href="products.html#manufacturing">Manufacturing Partnership</a></li>
                </ul>
            </div>
            
            <div class="footer-col">
                <h4>Contact Info</h4>
                <ul class="contact-info">
                <li>
                    <i class="fas fa-map-marker-alt"></i>
                    <span>Dubai Integrated Economic Zones (DSO), Dubai, UAE</span>
                </li>
                <li>
                    <i class="fas fa-phone"></i>
                    <span><a href="tel:+971585088518">+971 58-5088518</a></span>
                </li>
                <li>
                    <i class="fas fa-envelope"></i>
                    <span><a href="mailto:Info@naiveryacht.com">Info@naiveryacht.com</a></span>
                </li>
                <li>
                    <i class="fas fa-clock"></i>
                    <span>Monday - Friday: 9:00 AM - 6:00 PM</span>
                </li>
                </ul>
            </div>
            </div>
            
            <!-- Footer Bottom -->
            <div class="footer-bottom">
            <p>&copy; ${new Date().getFullYear()} NAVIER YACHTS FZCO. All Rights Reserved.</p>
            <div class="footer-links">
                <a href="privacy-policy.html">Privacy Policy</a>
                <a href="terms-of-service.html">Terms of Service</a>
                <a href="sitemap.html">Sitemap</a>
            </div>
            <a href="#" class="back-to-top">
                <i class="fas fa-arrow-up"></i>
            </a>
            </div>
        </div>
        `;
    }

    // Add event listener for back-to-top button
    const backToTopButton = document.querySelector('.back-to-top');
    if (backToTopButton) {
        backToTopButton.addEventListener('click', function(e) {
            e.preventDefault();
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // Show/hide back-to-top button based on scroll position
    window.addEventListener('scroll', function() {
        if (backToTopButton) {
            if (window.pageYOffset > 300) {
                backToTopButton.style.opacity = '1';
            } else {
                backToTopButton.style.opacity = '0';
            }
        }
    });
});
