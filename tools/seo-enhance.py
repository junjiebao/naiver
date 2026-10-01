#!/usr/bin/env python3
"""SEO hardening pass for the NAVIER YACHTS static site.

Adds / normalises, for every indexable page:
  * meta theme-color, og:locale, og:image (+ dimensions and alt), twitter:image
  * a semantic <nav> breadcrumb plus matching BreadcrumbList structured data
  * a WebPage node tying each page to the organisation

Homepage additionally gets an upgraded Organization node and a WebSite node.
Pages that had no structured data at all (privacy, terms, sitemap) get a
WebPage node.

Idempotent: safe to re-run. Run from the project root:

    python tools/seo-enhance.py
"""

from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

SITE = "https://www.navieryacht.com"
OG_IMAGE = f"{SITE}/images/og-image.jpg"
ORG_NAME = "NAVIER YACHTS FZCO"
THEME_COLOR = "#0A5D93"

# page -> (breadcrumb label, breadcrumb url path)
PAGES = {
    "about.html": ("About Us", "/about.html"),
    "products.html": ("Products & Services", "/products.html"),
    "projects.html": ("Projects", "/projects.html"),
    "news.html": ("News & Events", "/news.html"),
    "contact.html": ("Build Enquiry", "/contact.html"),
    "privacy-policy.html": ("Privacy Policy", "/privacy-policy.html"),
    "terms-of-service.html": ("Terms of Service", "/terms-of-service.html"),
    "sitemap.html": ("Sitemap", "/sitemap.html"),
}

ORGANIZATION = {
    "@context": "https://schema.org",
    "@type": ["Organization", "Manufacturer"],
    "@id": f"{SITE}/#organization",
    "name": ORG_NAME,
    "alternateName": "Navier Yachts",
    "url": SITE,
    "logo": {
        "@type": "ImageObject",
        "url": f"{SITE}/images/og-image.jpg",
        "width": 1200,
        "height": 630,
    },
    "image": OG_IMAGE,
    "description": (
        "Custom yacht construction and OEM manufacturing. Design and project management "
        "based in Dubai, production at the Longkou shipyard in Shandong, China. "
        "Aluminium catamarans, patrol vessels and commercial boats."
    ),
    "address": {
        "@type": "PostalAddress",
        "addressLocality": "Dubai",
        "addressRegion": "Dubai",
        "addressCountry": "AE",
    },
    "areaServed": [
        {"@type": "Country", "name": "United Arab Emirates"},
        {"@type": "Country", "name": "Oman"},
        {"@type": "Country", "name": "Saudi Arabia"},
        {"@type": "Country", "name": "Qatar"},
        {"@type": "Country", "name": "Kuwait"},
        {"@type": "Country", "name": "Bahrain"},
    ],
    "contactPoint": [
        {
            "@type": "ContactPoint",
            "contactType": "sales",
            "telephone": "+971585088518",
            "email": "info@navieryacht.com",
            "availableLanguage": ["en", "zh", "ar"],
            "areaServed": ["AE", "OM", "SA", "QA", "KW", "BH"],
        }
    ],
    "knowsAbout": [
        "custom yacht construction",
        "OEM boat manufacturing",
        "aluminium catamaran building",
        "patrol vessel construction",
        "naval architecture",
    ],
    "sameAs": [
        "https://wa.me/971585088518",
    ],
}

WEBSITE = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": f"{SITE}/#website",
    "url": SITE,
    "name": ORG_NAME,
    "publisher": {"@id": f"{SITE}/#organization"},
    "inLanguage": "en",
}

SERVICES = {
    "@context": "https://schema.org",
    "@type": "Service",
    "@id": f"{SITE}/products.html#service",
    "serviceType": "Custom yacht construction and OEM vessel manufacturing",
    "provider": {"@id": f"{SITE}/#organization"},
    "areaServed": {"@type": "Place", "name": "Worldwide"},
    "hasOfferCatalog": {
        "@type": "OfferCatalog",
        "name": "Vessel build programmes",
        "itemListElement": [
            {"@type": "Offer", "itemOffered": {"@type": "Product", "name": "TideMaster catamaran series"}},
            {"@type": "Offer", "itemOffered": {"@type": "Product", "name": "SnakeHead patrol and interceptor vessels"}},
            {"@type": "Offer", "itemOffered": {"@type": "Product", "name": "Hunter sport fishing boats"}},
            {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Contract and OEM boat building"}},
            {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "Naval engineering and design consultancy"}},
        ],
    },
}


def breadcrumb_node(page: str) -> dict:
    label, path = PAGES[page]
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": label, "item": f"{SITE}{path}"},
        ],
    }


def webpage_node(page: str) -> dict:
    if page == "index.html":
        url = f"{SITE}/"
        title = "Custom Yacht Construction & OEM Manufacturing"
    else:
        label, path = PAGES[page]
        url = f"{SITE}{path}"
        title = label

    node = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": f"{url}#webpage",
        "url": url,
        "name": title,
        "isPartOf": {"@id": f"{SITE}/#website"},
        "about": {"@id": f"{SITE}/#organization"},
        "inLanguage": "en",
    }
    if page in PAGES:
        node["breadcrumb"] = {"@id": f"{url}#breadcrumb"}
    return node


def strip_existing(text: str, pattern: str) -> str:
    return re.sub(pattern, "", text)


def ensure_meta(text: str, name: str, value: str, attr: str = "name") -> tuple[str, bool]:
    """Insert <meta attr="name" content="value"> if no such tag is present."""
    if re.search(rf'<meta {attr}="{re.escape(name)}"[^>]*>', text):
        return text, False
    tag = f'    <meta {attr}="{name}" content="{value}">\n'
    anchor = re.search(r'<meta name="viewport"[^>]*>\n', text)
    if anchor:
        return text[: anchor.end()] + tag + text[anchor.end():], True
    return text.replace("<head>\n", "<head>\n" + tag, 1), True


def inject_jsonld(text: str, payload: dict) -> str:
    block = (
        '    <script type="application/ld+json">\n'
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n    </script>\n"
    )
    marker = "    <title>"
    idx = text.find(marker)
    if idx == -1:
        return text.replace("</head>", block + "</head>", 1)
    return text[:idx] + block + text[idx:]


def process(page: str, path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    changes: list[str] = []

    # --- theme colour -------------------------------------------------
    text, added = ensure_meta(text, "theme-color", THEME_COLOR)
    if added:
        changes.append("theme-color")

    # --- locale -------------------------------------------------------
    text, added = ensure_meta(text, "og:locale", "en_US", attr="property")
    if added:
        changes.append("og:locale")

    # --- og:image: drop the narrow logo, use the 1200x630 card --------
    before = text
    text = strip_existing(text, r'[ \t]*<meta property="og:image"[^>]*>\n')
    text = strip_existing(text, r'[ \t]*<meta property="og:image:(?:width|height|alt|type|secure_url)"[^>]*>\n')
    text = strip_existing(text, r'[ \t]*<meta name="twitter:image[^"]*"[^>]*>\n')
    text = strip_existing(text, r'[ \t]*<meta property="twitter:image[^"]*"[^>]*>\n')

    og_block = (
        f'    <meta property="og:image" content="{OG_IMAGE}">\n'
        f'    <meta property="og:image:width" content="1200">\n'
        f'    <meta property="og:image:height" content="630">\n'
        f'    <meta property="og:image:type" content="image/jpeg">\n'
        f'    <meta property="og:image:alt" content="NAVIER YACHTS — custom yacht construction and OEM manufacturing">\n'
        f'    <meta name="twitter:image" content="{OG_IMAGE}">\n'
        f'    <meta name="twitter:image:alt" content="NAVIER YACHTS — custom yacht construction and OEM manufacturing">\n'
    )

    anchor = re.search(r'[ \t]*<meta property="og:url"[^>]*>\n', text)
    if anchor:
        text = text[: anchor.end()] + og_block + text[anchor.end():]
    elif "<title>" in text:
        text = text.replace("    <title>", og_block + "    <title>", 1)
    if text != before:
        changes.append("og:image")

    # --- twitter card -------------------------------------------------
    before = text
    text = re.sub(r'<meta name="twitter:card" content="[^"]*">',
                  '<meta name="twitter:card" content="summary_large_image">', text)
    if text != before:
        changes.append("twitter:card")

    # --- semantic breadcrumb ------------------------------------------
    before = text
    text = re.sub(
        r'<div class="breadcrumb">(.*?)</div>',
        r'<nav class="breadcrumb" aria-label="Breadcrumb">\1</nav>',
        text,
        flags=re.DOTALL,
    )
    if text != before:
        changes.append("breadcrumb-nav")

    # --- structured data ----------------------------------------------
    nodes = [webpage_node(page)]
    if page in PAGES:
        nodes.append(breadcrumb_node(page))
    if page == "index.html":
        nodes.extend([ORGANIZATION, WEBSITE])
    if page == "products.html":
        nodes.append(SERVICES)

    # Remove the hand-written Organization node on the homepage so the
    # upgraded one is authoritative.
    if page == "index.html":
        text = re.sub(
            r'[ \t]*<script type="application/ld\+json">\s*\{\s*"@context":\s*"https://schema\.org",\s*"@type":\s*"Organization".*?</script>\n',
            "",
            text,
            flags=re.DOTALL,
        )

    # Work out what the page already declares so we never double up.
    existing_ids: set[str] = set()
    existing_types: set[str] = set()
    for match in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', text, re.DOTALL):
        try:
            data = json.loads(match.group(1))
        except (ValueError, TypeError):
            continue
        for item in data if isinstance(data, list) else [data]:
            if not isinstance(item, dict):
                continue
            if item.get("@id"):
                existing_ids.add(item["@id"])
            node_type = item.get("@type")
            if isinstance(node_type, list):
                existing_types.update(node_type)
            elif node_type:
                existing_types.add(node_type)

    for node in nodes:
        node_id = node.get("@id")
        node_type = node.get("@type")
        type_label = node_type[0] if isinstance(node_type, list) else node_type

        if node_id and node_id in existing_ids:
            continue
        if not node_id and type_label in existing_types:
            continue

        text = inject_jsonld(text, node)
        changes.append(f"schema:{type_label}")
        if node_id:
            existing_ids.add(node_id)
        if isinstance(node_type, list):
            existing_types.update(node_type)
        else:
            existing_types.add(node_type)

    if text != path.read_text(encoding="utf-8"):
        path.write_text(text, encoding="utf-8")
    return changes


def main() -> None:
    for path in sorted(ROOT.glob("*.html")):
        if path.name == "404.html":
            continue
        changes = process(path.name, path)
        print(f"{path.name:24s} {'OK' if not changes else ', '.join(changes)}")


if __name__ == "__main__":
    main()
