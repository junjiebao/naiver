#!/usr/bin/env python3
"""Regenerate the static <header> and <footer> blocks in every page.

Why this exists
---------------
The header and footer used to be written into empty <header></header> /
<footer></footer> tags by header.js and footer.js at runtime. That meant:

  * crawlers received an empty header and footer, so the site's main internal
    link graph (every nav link and every footer link) was invisible without
    JavaScript execution;
  * the navigation and footer "popped in" after JS ran, causing layout shift;
  * with JavaScript disabled the site had no navigation at all.

The markup now lives in the HTML. This script is the single source of truth so
the nine pages cannot drift apart. Run it after editing HEADER or FOOTER:

    python tools/build-partials.py

Note: the templates below already carry the final optimised <img> markup
(WebP srcset, explicit sizes, loading hints, and the white footer logo). Keep it
that way — if you simplify a logo tag back to a bare `src`, you will undo the
responsive-image work in tools/optimize-images.py and reintroduce the footer
"white block" bug documented in tools/build-assets.py.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

NAV_ITEMS = [
    ("index.html", "Home", "NAVIER YACHTS — custom yacht construction and OEM manufacturing"),
    ("about.html", "About Us", "Our shipyards and manufacturing capability in Dubai and Longkou, China"),
    ("products.html", "Products &amp; Services", "Vessel platforms, OEM production and engineering services"),
    ("projects.html", "Projects", "Completed custom yacht and patrol vessel build projects"),
    ("news.html", "News &amp; Events", "Build updates, vessel launches and boat show appearances"),
    ("contact.html", "Build Enquiry", "Start a custom yacht or OEM build enquiry"),
]

HEADER = """<header>
    <div class="container">
        <div class="logo">
            <a href="index.html" aria-label="NAVIER YACHTS home">
                <img src="images/opt/logo-narrow-png-1019.webp" alt="NAVIER YACHTS" srcset="images/opt/logo-narrow-png-480.webp 480w, images/opt/logo-narrow-png-960.webp 960w, images/opt/logo-narrow-png-1019.webp 1019w" sizes="196px" width="1019" height="260" decoding="async" loading="eager">
            </a>
        </div>
        <nav aria-label="Main">
            <button type="button" class="menu-toggle" aria-label="Open navigation menu"
                    aria-expanded="false" aria-controls="nav-menu">
                <i class="fas fa-bars" aria-hidden="true"></i>
            </button>
            <ul class="nav-menu" id="nav-menu">
__NAV__
            </ul>
        </nav>
    </div>
</header>"""

FOOTER = """<footer>
    <div class="container">
        <!-- Footer Newsletter Section -->
        <div class="footer-newsletter">
            <div class="footer-newsletter-content">
                <div class="footer-newsletter-text">
                    <h3>Project &amp; Build Updates</h3>
                    <p>Receive updates on completed builds, new construction capabilities, and shipyard developments.</p>
                </div>
                <div class="footer-newsletter-form">
                    <form data-enquiry-kind="subscribe" action="/api/enquiry" method="post">
                        <label class="visually-hidden" for="footer-newsletter-email">Email address</label>
                        <input type="email" id="footer-newsletter-email" name="email"
                               placeholder="Enter your email address" autocomplete="email"
                               maxlength="254" required>
                        <div class="honeypot-field" aria-hidden="true">
                            <label for="footer-website">Leave this field empty</label>
                            <input type="text" id="footer-website" name="website" tabindex="-1" autocomplete="off">
                        </div>
                        <button type="submit" class="submit-btn">Subscribe</button>
                    </form>
                </div>
            </div>
        </div>

        <!-- Main Footer Content -->
        <div class="footer-content">
            <div class="footer-col">
                <img src="images/opt/logo-narrow-white-png-1019.webp" alt="NAVIER YACHTS" class="footer-logo" srcset="images/opt/logo-narrow-white-png-480.webp 480w, images/opt/logo-narrow-white-png-960.webp 960w, images/opt/logo-narrow-white-png-1019.webp 1019w" sizes="235px" width="1019" height="260" decoding="async" loading="lazy">
                <p>NAVIER YACHTS — Custom yacht construction &amp; OEM manufacturing. Dubai Design Center + Longkou,
                    China Production Shipyard. Engineered in Dubai. Built in China. Delivered worldwide.</p>
                <div class="social-links">
                    <a href="https://wa.me/971585088518" target="_blank" rel="noopener noreferrer"
                       aria-label="Chat with NAVIER YACHTS on WhatsApp"><i class="fab fa-whatsapp" aria-hidden="true"></i></a>
                    <a href="mailto:info@navieryacht.com" aria-label="Email NAVIER YACHTS"><i class="fas fa-envelope" aria-hidden="true"></i></a>
                    <a href="tel:+971585088518" aria-label="Call NAVIER YACHTS"><i class="fas fa-phone" aria-hidden="true"></i></a>
                </div>
            </div>

            <div class="footer-col">
                <h4>Quick Links</h4>
                <ul>
                    <li><a href="index.html">Home</a></li>
                    <li><a href="about.html">Our Shipyards &amp; Manufacturing</a></li>
                    <li><a href="products.html">Products &amp; Services</a></li>
                    <li><a href="projects.html">Completed Build Projects</a></li>
                    <li><a href="news.html">News &amp; Events</a></li>
                    <li><a href="contact.html">Start a Build Enquiry</a></li>
                </ul>
            </div>

            <div class="footer-col">
                <h4>Our Build Capabilities</h4>
                <ul>
                    <li><a href="products.html#tidemaster">TideMaster Catamarans</a></li>
                    <li><a href="products.html#Patrol">SnakeHead Patrol Vessels</a></li>
                    <li><a href="products.html#imported">Contract &amp; OEM Builds</a></li>
                    <li><a href="products.html#consultancy">Naval Engineering &amp; Design</a></li>
                    <li><a href="products.html#manufacturing">Aluminium Hull Fabrication</a></li>
                </ul>
            </div>

            <div class="footer-col">
                <h4>Contact Info</h4>
                <ul class="contact-info">
                    <li>
                        <i class="fas fa-map-marker-alt" aria-hidden="true"></i>
                        <span>Dubai Integrated Economic Zones (DSO), Dubai, UAE</span>
                    </li>
                    <li>
                        <i class="fas fa-industry" aria-hidden="true"></i>
                        <span>Longkou Production Shipyard, Shandong, China</span>
                    </li>
                    <li>
                        <i class="fas fa-phone" aria-hidden="true"></i>
                        <span><a href="tel:+971585088518">+971 58 508 8518</a></span>
                    </li>
                    <li>
                        <i class="fas fa-envelope" aria-hidden="true"></i>
                        <span><a href="mailto:info@navieryacht.com">info@navieryacht.com</a></span>
                    </li>
                    <li>
                        <i class="fas fa-clock" aria-hidden="true"></i>
                        <span>Monday - Friday: 9:00 AM - 6:00 PM (GST)</span>
                    </li>
                </ul>
            </div>
        </div>

        <!-- Footer Bottom -->
        <div class="footer-bottom">
            <p>&copy; <span class="footer-year">__YEAR__</span> NAVIER YACHTS FZCO. All Rights Reserved.</p>
            <div class="footer-links">
                <a href="privacy-policy.html">Privacy Policy</a>
                <a href="terms-of-service.html">Terms of Service</a>
                <a href="sitemap.html">Sitemap</a>
            </div>
            <a href="#" class="back-to-top" aria-label="Back to top">
                <i class="fas fa-arrow-up" aria-hidden="true"></i>
            </a>
        </div>
    </div>
</footer>"""

HEADER_RE = re.compile(r"<header>.*?</header>", re.DOTALL)
FOOTER_RE = re.compile(r"<footer>.*?</footer>", re.DOTALL)


def build_nav(current: str) -> str:
    lines = []
    for href, label, title in NAV_ITEMS:
        if href == current:
            lines.append(
                f'                <li><a href="{href}" class="active" aria-current="page" '
                f'title="{title}">{label}</a></li>'
            )
        else:
            lines.append(f'                <li><a href="{href}" title="{title}">{label}</a></li>')
    return "\n".join(lines)


def main() -> int:
    year = 2026
    updated = []
    problems = []

    for page in sorted(ROOT.glob("*.html")):
        if page.name == "footer-test.html":
            continue

        text = page.read_text(encoding="utf-8")
        original = text

        header = HEADER.replace("__NAV__", build_nav(page.name))
        footer = FOOTER.replace("__YEAR__", str(year))

        if HEADER_RE.search(text):
            text = HEADER_RE.sub(lambda _m: header, text, count=1)
        else:
            problems.append(f"{page.name}: no <header> block found")

        if FOOTER_RE.search(text):
            text = FOOTER_RE.sub(lambda _m: footer, text, count=1)
        else:
            problems.append(f"{page.name}: no <footer> block found")

        if text != original:
            page.write_text(text, encoding="utf-8")
            updated.append(page.name)

    print(f"updated {len(updated)} pages")
    for name in updated:
        print(f"  - {name}")
    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print(f"  ! {p}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
