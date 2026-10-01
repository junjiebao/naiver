#!/usr/bin/env python3
"""Point the header and footer logos at the right asset and the right sizes.

Two defects are corrected here:

1. The footer logo relied on `filter: brightness(0) invert(1)`, which on an
   opaque white-background source renders as a solid white rectangle. It now
   uses the transparent white asset built by tools/build-assets.py.
2. Both logo tags carried a generic `sizes` value borrowed from content images
   ("(max-width: 768px) 100vw, … 700px"), so the browser always picked a large
   candidate for a logo that renders at 196px (header) / 235px (footer). The
   header logo was also marked `loading="lazy"` despite being above the fold.

Idempotent: re-running makes no further changes.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

SRCSET_DARK = (
    'srcset="images/opt/logo-narrow-png-480.webp 480w, '
    'images/opt/logo-narrow-png-960.webp 960w, '
    'images/opt/logo-narrow-png-1019.webp 1019w"'
)
SRCSET_WHITE = (
    'srcset="images/opt/logo-narrow-white-png-480.webp 480w, '
    'images/opt/logo-narrow-white-png-960.webp 960w, '
    'images/opt/logo-narrow-white-png-1019.webp 1019w"'
)
GENERIC_SIZES = 'sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 700px"'

# Header: inside <header>, renders at height 50px => 196px wide, above the fold.
OLD_HEADER = (
    f'<img src="images/opt/logo-narrow-png-1019.webp" alt="NAVIER YACHTS" '
    f'{SRCSET_DARK} {GENERIC_SIZES} width="1019" height="260" '
    f'decoding="async" loading="lazy">'
)
NEW_HEADER = (
    f'<img src="images/opt/logo-narrow-png-1019.webp" alt="NAVIER YACHTS" '
    f'{SRCSET_DARK} sizes="196px" width="1019" height="260" '
    f'decoding="async" loading="eager">'
)

# Footer: renders at height 60px => 235px wide, below the fold.
OLD_FOOTER = (
    f'<img src="images/opt/logo-narrow-png-1019.webp" alt="NAVIER YACHTS" '
    f'class="footer-logo" {SRCSET_DARK} {GENERIC_SIZES} width="1019" '
    f'height="260" decoding="async" loading="lazy">'
)
NEW_FOOTER = (
    f'<img src="images/opt/logo-narrow-white-png-1019.webp" alt="NAVIER YACHTS" '
    f'class="footer-logo" {SRCSET_WHITE} sizes="235px" width="1019" '
    f'height="260" decoding="async" loading="lazy">'
)


def main() -> int:
    header_hits = footer_hits = unexpected = 0
    pages = sorted(ROOT.glob("*.html"))

    for page in pages:
        text = page.read_text(encoding="utf-8")
        original = text

        header_hits += text.count(OLD_HEADER)
        footer_hits += text.count(OLD_FOOTER)
        text = text.replace(OLD_HEADER, NEW_HEADER)
        text = text.replace(OLD_FOOTER, NEW_FOOTER)

        if text != original:
            page.write_text(text, encoding="utf-8")

        # Anything still carrying the generic sizes on a logo tag is a miss.
        for line in text.splitlines():
            if "logo-narrow" in line and GENERIC_SIZES in line:
                unexpected += 1
                print(f"  UNFIXED {page.name}: {line.strip()[:150]}")

    print(f"pages scanned:        {len(pages)}")
    print(f"header logo updated:  {header_hits}")
    print(f"footer logo updated:  {footer_hits}")
    print(f"still generic sizes:  {unexpected}")
    return 1 if unexpected else 0


if __name__ == "__main__":
    sys.exit(main())
