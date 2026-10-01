#!/usr/bin/env python3
"""Verify UTF-8 validity and absence of mojibake across the HTML pages.

A byte-order mark is *not* required: the charset is declared in each page's
<meta charset> tag, and a BOM is optional. The BOM column below is reported for
awareness only, so that the set stays consistent if anyone chooses to change it.

Fails only on genuine defects: undecodable bytes or mojibake markers.
"""
from __future__ import annotations

import pathlib
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOM = b"\xef\xbb\xbf"
# Mojibake markers: replacement char, and the classic C1/CP1252 mis-decodes.
MARKERS = ["\ufffd", "\u00c3\u00a9", "\u00e2\u20ac", "\u00c2\u00a0", "\u00e2\u20ac\u201d"]


def main() -> int:
    problems = 0
    for page in sorted(ROOT.glob("*.html")):
        raw = page.read_bytes()
        has_bom = raw[:3] == BOM
        try:
            text = raw.decode("utf-8")
            enc = "utf-8 OK"
        except UnicodeDecodeError as exc:
            enc = f"DECODE FAIL {exc}"
            problems += 1
            text = raw.decode("utf-8", errors="replace")

        markers = sum(text.count(m) for m in MARKERS)
        if markers:
            problems += 1

        print(f"{page.name:24s} BOM={str(has_bom):5s} {enc:14s} mojibake={markers}")

    # Non-ASCII inventory, to confirm intentional typography survived.
    chars: dict[str, int] = {}
    for page in sorted(ROOT.glob("*.html")):
        for ch in page.read_text(encoding="utf-8"):
            if ord(ch) > 127 and ch != "\ufeff":
                chars[ch] = chars.get(ch, 0) + 1
    print("\ndistinct non-ASCII chars:", len(chars))
    for ch, n in sorted(chars.items(), key=lambda kv: -kv[1])[:25]:
        try:
            name = unicodedata.name(ch)
        except ValueError:
            name = "?"
        print(f"  U+{ord(ch):04X}  {ch}  x{n:<5d} {name}")

    leftover = sum(
        p.read_text(encoding="utf-8").count("naiveryacht") for p in ROOT.rglob("*.html")
    )
    print("\nremaining 'naiveryacht' typos:", leftover)
    print("problems:", problems)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
