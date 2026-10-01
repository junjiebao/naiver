#!/usr/bin/env python3
"""Pre-deployment validation for the NAVIER YACHTS static site.

Checks performed
----------------
1. Every local src/href points at a file that actually exists on disk.
   (This is the check that would have caught the renamed-logo breakage.)
2. Every JSON-LD block parses; trailing stray braces are repaired.
3. No duplicate canonical / og:image / theme-color tags.
4. Required head elements present on every indexable page.
5. No Windows backslashes in path attributes.
6. No leftover non-www naiveryacht.com URLs.
7. No placeholder href="#" links outside the deliberate back-to-top control.
8. Form endpoints wired to /api/enquiry on every page that contains a form.

Exits non-zero when a hard failure is found.

    python tools/validate.py [--fix]
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = "--fix" in sys.argv

SKIP_PAGES = {"404.html"}

failures: list[str] = []
warnings: list[str] = []


def report(kind: str, message: str) -> None:
    (failures if kind == "FAIL" else warnings).append(f"{kind}: {message}")


# ---------------------------------------------------------------- resources

ATTR_RE = re.compile(r'(?:src|href|srcset|poster)="([^"]+)"')
PAGE_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)


def resolve(page: pathlib.Path, raw: str) -> pathlib.Path | None:
    """Resolve a relative reference from a page to an on-disk path."""
    if not raw:
        return None
    if raw.startswith(("http://", "https://", "//", "#", "mailto:", "tel:", "data:", "javascript:")):
        return None
    cleaned = raw.split("?")[0].split("#")[0]
    if not cleaned:
        return None
    if cleaned.startswith("/"):
        return ROOT / cleaned.lstrip("/")
    return page.parent / cleaned


def check_resources(page: pathlib.Path, text: str) -> None:
    # srcset holds a comma-separated list where each entry may carry a width or
    # density descriptor after the URL.
    for raw in re.findall(r'srcset="([^"]+)"', text):
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            url = part.split()[0] if " " in part else part
            target = resolve(page, url)
            if target is not None and not target.exists():
                report("FAIL", f"{page.name}: missing local resource -> {url}")

    # src / href / poster carry a single URL that may legitimately contain spaces.
    for raw in re.findall(r'(?:src|href|poster)="([^"]+)"', text):
        target = resolve(page, raw)
        if target is not None and not target.exists():
            report("FAIL", f"{page.name}: missing local resource -> {raw}")


# ---------------------------------------------------------------- json-ld

def repair_jsonld(block: str) -> tuple[str, bool]:
    """Drop stray trailing braces until the block parses."""
    body = block.strip()
    for _ in range(6):
        try:
            json.loads(body)
            return body, body != block.strip()
        except json.JSONDecodeError:
            stripped = body.rstrip()
            if not stripped.endswith("}"):
                return block, False
            body = stripped[:-1]
    return block, False


def check_jsonld(page: pathlib.Path, text: str) -> str:
    for index, block in enumerate(PAGE_RE.findall(text)):
        try:
            json.loads(block)
        except json.JSONDecodeError as error:
            if FIX:
                repaired, changed = repair_jsonld(block)
                if changed:
                    try:
                        json.loads(repaired)
                        text = text.replace(block, "\n" + repaired + "\n", 1)
                        report("WARN", f"{page.name}: repaired malformed JSON-LD block {index}")
                        continue
                    except json.JSONDecodeError:
                        pass
            report("FAIL", f"{page.name}: JSON-LD block {index} does not parse -> {error}")
    return text


def check_jsonld_urls(page: pathlib.Path, text: str) -> None:
    for block in PAGE_RE.findall(text):
        for url in re.findall(r'"(https?://[^"]*)"', block):
            if " " in url:
                report("FAIL", f"{page.name}: unencoded space in JSON-LD URL -> {url}")


# ---------------------------------------------------------------- head tags

def count_matches(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text))


def main() -> int:
    pages = sorted(p for p in ROOT.glob("*.html"))
    print(f"validating {len(pages)} pages\n")

    for page in pages:
        text = page.read_text(encoding="utf-8")
        original = text

        text = check_jsonld(page, text)

        if text != original:
            page.write_text(text, encoding="utf-8")

        check_resources(page, text)
        check_jsonld_urls(page, text)

        # duplicate head tags
        for pattern, label in (
            (r'<link rel="canonical"', "canonical"),
            (r'<meta property="og:image" ', "og:image"),
            (r'<meta name="theme-color"', "theme-color"),
            (r'<title>', "title"),
        ):
            n = count_matches(pattern, text)
            if n > 1:
                report("FAIL", f"{page.name}: {n} x {label} tags (expected 1)")
            elif n == 0 and page.name not in SKIP_PAGES and label != "theme-color":
                report("FAIL", f"{page.name}: missing {label}")

        # required head elements on indexable pages
        if page.name not in SKIP_PAGES:
            for needle, label in (
                ('name="viewport"', "viewport"),
                ('name="description"', "meta description"),
                ("js/forms.js", "form handler script"),
                ('<link rel="stylesheet" href="css/style.css">', "main stylesheet"),
            ):
                if needle not in text:
                    report("FAIL", f"{page.name}: missing {label}")

        # static navigation must be in the HTML, not injected
        if page.name not in SKIP_PAGES:
            if '<ul class="nav-menu"' not in text:
                report("FAIL", f"{page.name}: nav menu not present in static HTML")
            if 'class="footer-col"' not in text:
                report("FAIL", f"{page.name}: footer not present in static HTML")

        # backslashes in path attributes
        for attr, value in re.findall(r'(src|href|srcset)="([^"]*)"', text):
            if "\\" in value:
                report("FAIL", f"{page.name}: backslash in {attr} -> {value}")

        # non-www domain leftovers
        for bad in re.findall(r"https://naiveryacht\.com[^\"]*", text):
            report("FAIL", f"{page.name}: non-www URL -> {bad}")

        # Placeholder links. Two forms are legitimate and expected:
        #   * the back-to-top control
        #   * JS-driven reveal triggers carrying data-article / data-project
        for match in re.finditer(r'<a\b[^>]*href="#"[^>]*>', text):
            tag = match.group(0)
            if "back-to-top" in tag:
                continue
            if "data-article=" in tag or "data-project=" in tag:
                continue
            report("FAIL", f"{page.name}: placeholder link -> {tag[:110]}")

        # forms must post to the API
        if "<form" in text:
            for form_tag in re.findall(r"<form\b[^>]*>", text):
                if 'action="/api/enquiry"' not in form_tag:
                    report("FAIL", f"{page.name}: form not wired to /api/enquiry -> {form_tag[:110]}")
                if "data-enquiry-kind" not in form_tag:
                    report("FAIL", f"{page.name}: form missing data-enquiry-kind")

    # backend prerequisites
    fn = ROOT / "node-functions" / "api" / "enquiry.js"
    if not fn.exists():
        report("FAIL", "node-functions/api/enquiry.js is missing")
    else:
        source = fn.read_text(encoding="utf-8")
        for needle, label in (
            ("LARK_WEBHOOK_URL", "webhook env var"),
            ("LARK_WEBHOOK_SECRET", "secret env var"),
            ("createHmac", "signature implementation"),
        ):
            if needle not in source:
                report("FAIL", f"enquiry.js missing {label}")
        # Only real credential material counts; the API hostname is public
        # documentation, not a secret.
        for leaked in ("13a17204-ab00", "pMzY2oO2LTjxjVzPkP3XFb"):
            if leaked in source:
                report("FAIL", f"enquiry.js leaks a live credential fragment ({leaked[:14]}...)")

    # secret material must never appear in the public site
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for leaked in ("pMzY2oO2LTjxjVzPkP3XFb", "13a17204-ab00-4457"):
            if leaked in text:
                report("FAIL", f"{page.name}: contains live Lark credential material")
            # Misspelled domain. `naiveryacht.com` is not the company's domain and
            # has no MX records, so a mailto: or a JSON-LD email pointing at it
            # bounces silently. This exact bug shipped to production once already,
            # in 46 places, so it is now an asserted invariant rather than a
            # convention.
            if "naiveryacht.com" in text:
                report(
                    "FAIL",
                    f"{page.name}: misspelled domain 'naiveryacht.com' "
                    f"(must be navieryacht.com)",
                )

        if "mailto:" in text and "info@navieryacht.com" not in text:
            report("FAIL", f"{page.name}: mailto: link but no info@navieryacht.com")

    # the same typo must not live in shipped JS or the serverless function
    for extra in (
        ROOT / "js" / "main.js",
        ROOT / "js" / "forms.js",
        ROOT / "node-functions" / "api" / "enquiry.js",
        ROOT / "robots.txt",
        ROOT / "sitemap.xml",
    ):
        if extra.exists() and "naiveryacht.com" in extra.read_text(encoding="utf-8"):
            report("FAIL", f"{extra.relative_to(ROOT).as_posix()}: misspelled domain")

    # Every <img> carries width/height presentation attributes so the browser can
    # reserve space. For an image sized by CSS height alone that attribute would
    # otherwise win the other axis: the logo rendered 706x50 instead of 196x50,
    # which squeezed the navigation onto two lines and grew the header past the
    # 80px that `body { padding-top: 80px }` reserves. So every selector that
    # sizes an image by a bare `height` must pin `width: auto` somewhere in its
    # own rule set.
    # Flags are collected per selector rather than per rule, because a media
    # query is allowed to override just the height (`.model-card img` does that)
    # while the width lives on in the base rule.
    # `(?<![-\w])` keeps `line-height` from counting as a height declaration.
    HEIGHT_DECL = re.compile(r"(?<![-\w])height\s*:\s*([^;}]+)")
    WIDTH_DECL = re.compile(r"(?<![-\w])width\s*:\s*([^;}]+)")
    TARGETS_IMAGE = re.compile(r"(?:^|[\s,>+~])img(?:\b|$)")
    for css_name in ("style.css", "hero.css"):
        style = (ROOT / "css" / css_name).read_text(encoding="utf-8")
        style = re.sub(r"/\*[\s\S]*?\*/", "", style)

        sized_by_height: set[str] = set()
        has_width: set[str] = set()
        cropped: set[str] = set()
        solved: set[str] = set()
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", style):
            selector, body = match.group(1).strip(), match.group(2)
            # `img` type selectors, plus the brand marks that are classes on <img>.
            if not (TARGETS_IMAGE.search(selector) or "logo" in selector):
                continue
            if "object-fit" in body:
                cropped.add(selector)
            if WIDTH_DECL.search(body):
                has_width.add(selector)
            heights = HEIGHT_DECL.findall(body)
            if heights and not all("auto" in h for h in heights):
                sized_by_height.add(selector)
            if HEIGHT_DECL.search(body) and re.search(r"height\s*:\s*auto", body):
                solved.add(selector)

        for selector in sorted(sized_by_height):
            if selector in has_width or selector in cropped or selector in solved:
                continue
            report(
                "FAIL",
                f"css/{css_name}: '{selector}' sizes an image by height without "
                f"`width: auto`, so the <img> width attribute decides the ratio",
            )

    print(f"failures: {len(failures)}")
    for item in failures:
        print(f"  {item}")
    print(f"\nwarnings: {len(warnings)}")
    for item in warnings:
        print(f"  {item}")

    if not failures:
        print("\nAll checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
