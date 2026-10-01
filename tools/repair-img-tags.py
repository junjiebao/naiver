#!/usr/bin/env python3
"""One-off repair for <img> tags damaged by a buggy attribute-append.

The first version of tools/optimize-images.py appended attributes with
`tag[:-1] + ' attr="value"'`, which removed one character before each append.
Because the tag's closing ">" had already been stripped, that removed the
closing quote of the previously appended attribute instead.

The damage is fully deterministic, so it can be inverted exactly:
    sizes="V width="W" height="H decoding="async loading="lazy">
becomes
    sizes="V" width="W" height="H" decoding="async" loading="lazy">

Run once, then delete this file:
    python tools/repair-img-tags.py
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Ordered: fix the innermost loss first, working outwards.
REPAIRS = [
    (r'decoding="async loading="lazy"', 'decoding="async" loading="lazy"'),
    (r'height="(\d+) decoding=', r'height="\1" decoding='),
    (r'height="(\d+) loading="lazy"', r'height="\1" loading="lazy"'),
    (r'width="(\d+) height="(\d+) decoding=', r'width="\1" height="\2" decoding='),
    (r'width="(\d+) height="(\d+) loading="lazy"', r'width="\1" height="\2" loading="lazy"'),
    (r'sizes="((?:[^">]|"(?!\s))*?)\s+width="(\d+)"', r'sizes="\1" width="\2"'),
    (r'sizes="((?:[^">]|"(?!\s))*?)\s+decoding=', r'sizes="\1" decoding='),
    (r'sizes="((?:[^">]|"(?!\s))*?)\s+loading=', r'sizes="\1" loading='),
]

IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
VALID_RE = re.compile(r'^<img(\s+[a-zA-Z-]+="[^"]*")+\s*/?>$')


def repair_tag(tag: str) -> str:
    for pattern, replacement in REPAIRS:
        tag = re.sub(pattern, replacement, tag, count=0)
    return tag


def main() -> int:
    total_repaired = 0
    total_tags = 0
    invalid: list[str] = []

    for page in sorted(ROOT.glob("*.html")):
        text = page.read_text(encoding="utf-8")
        original = text
        repaired_here = 0

        def fix(match: "re.Match[str]") -> str:
            nonlocal repaired_here
            tag = match.group(0)
            fixed = repair_tag(tag)
            if fixed != tag:
                repaired_here += 1
            return fixed

        text = IMG_RE.sub(fix, text)

        if text != original:
            page.write_text(text, encoding="utf-8")

        # Verify every tag now parses as a well-formed set of quoted attributes.
        for tag in IMG_RE.findall(text):
            total_tags += 1
            if not VALID_RE.match(tag):
                invalid.append(f"{page.name}: {tag[:160]}")

        total_repaired += repaired_here
        if repaired_here:
            print(f"  {page.name:24s} repaired {repaired_here} tags")

    print(f"\nrepaired {total_repaired} of {total_tags} <img> tags")

    if invalid:
        print(f"\nSTILL MALFORMED ({len(invalid)}):")
        for item in invalid[:20]:
            print(f"  {item}")
        return 1

    print("all <img> tags are now well-formed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
