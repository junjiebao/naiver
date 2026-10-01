#!/usr/bin/env python3
"""One-off migration for the NAVIER YACHTS static site.

Applies the mechanical, site-wide corrections identified in the audit:
  * canonical / og:url / JSON-LD URLs -> https://www.navieryacht.com
  * homepage canonical -> "/" instead of "/index.html"
  * "images/logo narrow.png" -> "images/logo-narrow.png"
  * Windows backslashes in src/srcset attributes -> forward slashes
  * remove obsolete <meta name="keywords"> and hashtag keywords
  * Font Awesome beta -> 6.7.2 with a correct SRI hash
  * preconnect / dns-prefetch for the icon CDN
  * favicon + apple-touch-icon
  * load js/forms.js on every page
"""

import re
import pathlib

ROOT = pathlib.Path(r"D:/GitHub works/naiver")
FA_URL = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css"
FA_SRI = "sha512-Evv84Mr4kqVGRNSgIGL/F/aIDqQb7xQ2vcrdIwxfjThSH8CSR7PBEakCr51Ck+w+/U6swU2Im1vVX0SVk9ABhg=="

report = []


def process(path: pathlib.Path) -> None:
    original = path.read_text(encoding="utf-8")
    text = original
    changes = []

    # 1. Domain normalisation -> www
    new = re.sub(r"https://naiveryacht\.com", "https://www.navieryacht.com", text)
    if new != text:
        changes.append("domain->www")
        text = new

    # 2. Homepage canonical / og:url: drop the trailing index.html
    new = text.replace("https://www.navieryacht.com/index.html", "https://www.navieryacht.com/")
    if new != text:
        changes.append("homepage-url")
        text = new

    # 3. Logo filename: remove the space that breaks JSON-LD / og:image URLs
    new = text.replace("images/logo%20narrow.png", "images/logo-narrow.png")
    new = new.replace("images/logo narrow.png", "images/logo-narrow.png")
    if new != text:
        changes.append("logo-rename")
        text = new

    # 4. Backslashes inside src / srcset / href attributes
    def fix_backslashes(match: "re.Match[str]") -> str:
        attr, value = match.group(1), match.group(2)
        return f'{attr}="{value.replace(chr(92), "/")}"'

    new = re.sub(r'(src|srcset|href)="([^"]*)"', fix_backslashes, text)
    if new != text:
        backslash_count = text.count("\\") - new.count("\\")
        if backslash_count:
            changes.append(f"backslash-paths({backslash_count})")
        text = new

    # 5. Drop obsolete keyword meta tags
    new = re.sub(r'[ \t]*<meta name="keywords" content="[^"]*">\r?\n', "", text)
    new = re.sub(r'[ \t]*<meta name="keywords-hashtags" content="[^"]*">\r?\n', "", new)
    if new != text:
        changes.append("keywords-removed")
        text = new

    # 6. Font Awesome upgrade + SRI
    new = re.sub(
        r'https://cdnjs\.cloudflare\.com/ajax/libs/font-awesome/[^"]+/css/all\.min\.css',
        FA_URL,
        text,
    )
    new = re.sub(
        r'(<link rel="stylesheet" href="' + re.escape(FA_URL) + r'")\s+integrity="[^"]*"',
        r'\1 integrity="' + FA_SRI + '"',
        new,
    )
    if new != text:
        changes.append("fontawesome")
        text = new

    # 7. preconnect for the icon CDN (was only present on about.html)
    if "preconnect" not in text and FA_URL in text:
        text = text.replace(
            "    <link rel=\"stylesheet\" href=\"" + FA_URL + "\"",
            "    <link rel=\"preconnect\" href=\"https://cdnjs.cloudflare.com\" crossorigin>\n"
            "    <link rel=\"dns-prefetch\" href=\"https://cdnjs.cloudflare.com\">\n"
            "    <link rel=\"stylesheet\" href=\"" + FA_URL + "\"",
            1,
        )
        changes.append("preconnect")

    # 8. Favicon set (replace the ad-hoc one on about.html, add everywhere else)
    text = re.sub(r'[ \t]*<link rel="icon"[^>]*>\r?\n', "", text)
    if 'rel="apple-touch-icon"' not in text:
        favicon_block = (
            '    <link rel="icon" href="/favicon.ico" sizes="any">\n'
            '    <link rel="icon" type="image/svg+xml" href="/favicon.svg">\n'
            '    <link rel="apple-touch-icon" href="/apple-touch-icon.png">\n'
        )
        text = text.replace("    <link rel=\"stylesheet\" href=\"css/style.css\">",
                            favicon_block + "    <link rel=\"stylesheet\" href=\"css/style.css\">", 1)
        changes.append("favicon")

    # 9. Make sure the form handler is loaded on every page
    if "js/forms.js" not in text:
        if '<script src="js/footer.js"></script>' in text:
            text = text.replace(
                '<script src="js/footer.js"></script>',
                '<script src="js/footer.js"></script>\n<script src="js/forms.js"></script>',
                1,
            )
            changes.append("forms.js")
        elif "</body>" in text:
            text = text.replace(
                "</body>", '<script src="js/forms.js"></script>\n</body>', 1
            )
            changes.append("forms.js")

    if text != original:
        path.write_text(text, encoding="utf-8")
        report.append(f"{path.name}: {', '.join(changes)}")


for page in sorted(ROOT.glob("*.html")):
    process(page)

for extra in ("sitemap.xml", "robots.txt"):
    p = ROOT / extra
    if p.exists():
        process(p)

print("\n".join(report) if report else "no changes")
print(f"\nprocessed {len(list(ROOT.glob('*.html')))} html files")
