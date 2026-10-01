#!/usr/bin/env python3
"""Escape bare ampersands in HTML text and attribute values.

HTML requires a literal ampersand to be written as `&amp;`. A bare `&` is
tolerated by browsers in most positions, which is exactly why it survives for
years — but it is invalid markup, and strict consumers (feed readers, AMP
validators, XML tooling, some SEO crawlers) can choke on it.

Critically, this script must NOT touch:

  * <script> blocks        - script content is raw text; entities are NOT
                             decoded, so escaping a `&&` or a JSON-LD value
                             would corrupt the JavaScript / structured data.
  * <style> blocks         - same reason; `&` is a valid CSS nesting token.
  * HTML comments          - comments are not parsed for entities, and
                             rewriting them just makes diffs noisy.

Already-correct entities (`&amp;`, `&#8212;`, `&mdash;`, …) are left alone.

Usage:
    python tools/escape-ampersands.py            # report what would change
    python tools/escape-ampersands.py --write     # apply
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Regions whose contents must be left byte-for-byte untouched.
PROTECTED_RE = re.compile(
    r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<!--[\s\S]*?-->",
    re.IGNORECASE,
)

ENTITY_RE = re.compile(
    r"&(?:[a-zA-Z][a-zA-Z0-9]{1,31}|#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6});"
)


def escape_segment(segment: str) -> tuple[str, int]:
    """Return (escaped, count) for a segment known to contain no protected regions."""
    out: list[str] = []
    count = 0
    pos = 0
    for match in re.finditer(r"&", segment):
        tail = segment[match.start():]
        if ENTITY_RE.match(tail):
            continue
        out.append(segment[pos:match.start()])
        out.append("&amp;")
        pos = match.end()
        count += 1
    out.append(segment[pos:])
    return "".join(out), count


def process(text: str) -> tuple[str, int]:
    pieces: list[str] = []
    total = 0
    last = 0
    for match in PROTECTED_RE.finditer(text):
        head, n = escape_segment(text[last:match.start()])
        pieces.append(head)
        pieces.append(match.group(0))  # verbatim
        total += n
        last = match.end()
    tail, n = escape_segment(text[last:])
    pieces.append(tail)
    total += n
    return "".join(pieces), total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write changes to disk")
    args = ap.parse_args()

    grand_total = 0
    touched = 0
    for page in sorted(ROOT.glob("*.html")):
        text = page.read_text(encoding="utf-8")
        fixed, count = process(text)
        if not count:
            continue
        grand_total += count
        touched += 1
        print(f"  {page.name:24s} {count:3d} bare ampersand(s)")
        if args.write:
            page.write_text(fixed, encoding="utf-8")

    verb = "escaped" if args.write else "would escape"
    print(f"\n{verb} {grand_total} bare ampersand(s) across {touched} file(s)")
    if not args.write and grand_total:
        print("re-run with --write to apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
