#!/usr/bin/env python3
"""Scan the static site for development debris and quality regressions.

Categories:
  1. CJK characters (site is English-only; leftovers from the CN team leak)
  2. TODO / FIXME / XXX / HACK / DEBUG markers
  3. Lorem ipsum placeholder copy
  4. Inline event handlers (onclick/onsubmit/...) — belong in js/main.js
  5. Duplicate element ids within a page
  6. target="_blank" without rel="noopener"
  7. Empty/placeholder hrefs (href="#" with no role, href="")
  8. Images without alt
  9. Inline style="" usage count (informational)
 10. Broken internal links (href to a local file that does not exist)

Usage:
    python tools/debris-scan.py            # report
    python tools/debris-scan.py --strict   # exit 1 if any hard failures
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent

CJK_RE = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]")
MARKER_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK|DEBUG|WIP)\b")
LOREM_RE = re.compile(r"lorem ipsum", re.IGNORECASE)
# Only HTML attribute handlers: must appear inside a tag (preceded by "<tag ...").
INLINE_EVENT_RE = re.compile(r"<[a-zA-Z][^>]*?\son(click|submit|change|mouseover)\s*=", re.IGNORECASE)
ID_RE = re.compile(r'\sid="([^"]+)"')
TARGET_BLANK_RE = re.compile(r'<a\b[^>]*target="_blank"[^>]*>', re.IGNORECASE)
IMG_ALT_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
HREF_RE = re.compile(r'\shref="([^"]+)"')
ATTR_ALT_RE = re.compile(r'\salt="([^"]*)"')
STYLE_ATTR_RE = re.compile(r'\sstyle="([^"]*)"')

# hrefs that legitimately point nowhere.
HREF_EXEMPT = re.compile(r"^(#|mailto:|tel:|https?:|//|javascript:|\?)")

# Anchors handled by inline page scripts / role attributes rather than a file.
ANCHOR_OK = {"#", ""}


def local_target(page: pathlib.Path, href: str) -> pathlib.Path | None:
    """Resolve a local href to a filesystem path, or None if not local."""
    if HREF_EXEMPT.match(href):
        return None
    path = href.split("#")[0].split("?")[0]
    if not path or path == "/":
        return None
    # A leading "/" means "site root", which maps to ROOT (not the drive root).
    return (ROOT / path.lstrip("/")).resolve()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    pages = sorted(ROOT.glob("*.html"))
    findings: dict[str, list[str]] = {}
    info: dict[str, object] = {}

    cjk_total = 0
    style_total = 0
    blank_noopener: list[str] = []
    broken_links: list[str] = []

    for page in pages:
        text = page.read_text(encoding="utf-8")
        rel = page.name

        # 1. CJK
        for i, line in enumerate(text.splitlines(), 1):
            if CJK_RE.search(line):
                findings.setdefault("CJK characters", []).append(
                    f"{rel}:{i}  {line.strip()[:140]}"
                )
                cjk_total += 1

        # 2. markers
        for m in MARKER_RE.finditer(text):
            line = text[: m.start()].count("\n") + 1
            findings.setdefault("dev markers", []).append(
                f"{rel}:{line}  {m.group(1)}"
            )

        # 3. lorem ipsum
        if LOREM_RE.search(text):
            findings.setdefault("lorem ipsum", []).append(rel)

        # 4. inline event handlers
        for m in INLINE_EVENT_RE.finditer(text):
            line = text[: m.start()].count("\n") + 1
            findings.setdefault("inline event handlers", []).append(
                f"{rel}:{line}  {m.group(0).strip()}"
            )

        # 5. duplicate ids
        ids = ID_RE.findall(text)
        dups = [k for k, v in Counter(ids).items() if v > 1]
        if dups:
            findings.setdefault("duplicate ids", []).append(f"{rel}  {sorted(dups)}")

        # 6. target=_blank without noopener
        for tag in TARGET_BLANK_RE.findall(text):
            if "noopener" not in tag:
                blank_noopener.append(f"{rel}  {tag[:110]}")

        # 7. empty/placeholder anchors with no interactive role
        for tag in re.findall(r"<a\b[^>]*>", text, re.IGNORECASE):
            if re.search(r'\shref="#?"', tag) and "role=" not in tag:
                if "back-to-top" not in tag:
                    findings.setdefault("placeholder anchors", []).append(
                        f"{rel}  {tag[:110]}"
                    )

        # 8. images without alt
        for tag in IMG_ALT_RE.findall(text):
            if not ATTR_ALT_RE.search(tag):
                findings.setdefault("img without alt", []).append(f"{rel}  {tag[:110]}")

        # 9. inline styles (informational)
        style_total += len(STYLE_ATTR_RE.findall(text))

        # 10. broken local links
        for href in HREF_RE.findall(text):
            target = local_target(page, href.strip())
            if target is None:
                continue
            if not target.exists():
                broken_links.append(f"{rel} -> {href}")

    if blank_noopener:
        findings["target=_blank w/o rel=noopener"] = blank_noopener
    if broken_links:
        findings["broken local links"] = sorted(set(broken_links))

    info["inline style attributes"] = style_total
    info["CJK lines"] = cjk_total

    hard = 0
    if not findings:
        print("No debris found.")
    for category, items in findings.items():
        hard += len(items)
        print(f"\n### {category}  ({len(items)})")
        for item in items[:60]:
            print(f"  - {item}")
        if len(items) > 60:
            print(f"  ... and {len(items) - 60} more")

    print("\n### informational")
    for k, v in info.items():
        print(f"  {k}: {v}")

    print(f"\nhard findings: {hard}")
    return 1 if (args.strict and hard) else 0


if __name__ == "__main__":
    sys.exit(main())
