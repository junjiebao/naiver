#!/usr/bin/env python3
"""Optimise the site's imagery and rewrite the markup to use it.

For every raster image under images/ this script generates WebP variants at
several widths, then rewrites each referencing <img> tag so the browser can
pick an appropriately sized file.

Why: the original JPEGs and PNGs total ~53 MB, with single files up to 4.8 MB
being served verbatim. Originals are left on disk untouched (they remain the
source of truth for print and marketing use).

    python tools/optimize-images.py [--dry-run]
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMAGES = ROOT / "images"
OUT = IMAGES / "opt"
MANIFEST = ROOT / "tools" / "image-manifest.json"

WIDTHS = (480, 960, 1600)
QUALITY = 80
SOURCE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
DRY_RUN = "--dry-run" in sys.argv

# Container class -> sizes attribute. Chosen by scanning back from the <img>.
SIZE_RULES = [
    ("hero-slide", "100vw"),
    ("progress-gallery", "100vw"),
    ("large-news-item", "(max-width: 768px) 100vw, 60vw"),
    ("large-project-item", "(max-width: 768px) 100vw, 60vw"),
    ("project-article-images", "(max-width: 768px) 100vw, 45vw"),
    ("article-images", "(max-width: 768px) 100vw, 45vw"),
    ("news-image", "(max-width: 768px) 100vw, 40vw"),
    ("project-image", "(max-width: 768px) 100vw, 40vw"),
    ("gallery", "(max-width: 768px) 100vw, 33vw"),
    ("model-image", "(max-width: 768px) 100vw, 45vw"),
]
DEFAULT_SIZES = "(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 700px"


def slugify(rel: pathlib.Path) -> str:
    parts = [re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-") for p in rel.parts]
    return "-".join(p for p in parts if p)


def build_variants() -> dict:
    """Generate WebP variants and return {relative_src: variant_info}."""
    manifest: dict[str, dict] = {}
    used_slugs: set[str] = set()
    created = 0
    saved_bytes = 0

    sources = [
        p for p in sorted(IMAGES.rglob("*"))
        if p.is_file()
        and p.suffix.lower() in SOURCE_EXT
        and OUT not in p.parents
    ]

    for src in sources:
        rel = src.relative_to(IMAGES)
        slug = slugify(rel)
        while slug in used_slugs:
            slug += "-x"
        used_slugs.add(slug)

        try:
            with Image.open(src) as im:
                im.load()
                width, height = im.size
                # JPEGs have no alpha; keep PNG alpha where it exists.
                has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
                rgb = im.convert("RGBA" if has_alpha else "RGB")
        except Exception as error:  # unreadable file — leave it alone
            print(f"  SKIP {rel} ({error})")
            continue

        widths = [w for w in WIDTHS if w <= width] or [width]
        if width not in widths and width < max(WIDTHS):
            widths.append(width)
        widths = sorted(set(widths))

        variants: dict[str, str] = {}
        for w in widths:
            target_h = max(1, round(height * w / width))
            variant = rgb.resize((w, target_h), Image.LANCZOS)
            rel_out = pathlib.Path(str(rel.parent)) / f"{slug}-{w}.webp"
            out_path = OUT / rel_out
            out_path.parent.mkdir(parents=True, exist_ok=True)

            if not DRY_RUN:
                variant.save(out_path, "WEBP", quality=QUALITY, method=6)
            variants[str(w)] = str(pathlib.Path("images") / "opt" / rel_out).replace("\\", "/")
            created += 1

        original_size = src.stat().st_size
        largest = OUT / pathlib.Path(str(rel.parent)) / f"{slug}-{widths[-1]}.webp"
        if not DRY_RUN and largest.exists():
            saved_bytes += max(0, original_size - largest.stat().st_size * (max(widths) / width))
        elif DRY_RUN:
            saved_bytes += original_size

        manifest[str(rel).replace("\\", "/")] = {
            "width": width,
            "height": height,
            "slug": slug,
            "variants": variants,
            "original_bytes": original_size,
        }

    print(f"generated {created} WebP variants for {len(manifest)} source images")
    return manifest


def sizes_for(context: str) -> str:
    for needle, sizes in SIZE_RULES:
        if needle in context:
            return sizes
    return DEFAULT_SIZES


IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


def rewrite_page(path: pathlib.Path, manifest: dict) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    original = text
    rewritten = 0
    skipped = 0

    def replace_tag(match: "re.Match[str]") -> str:
        nonlocal rewritten, skipped
        tag = match.group(0)

        src_match = re.search(r'src="([^"]+)"', tag)
        if not src_match:
            skipped += 1
            return tag

        raw_src = src_match.group(1)
        key = raw_src.replace("\\", "/")
        if key.startswith("/"):
            key = key[1:]
        if key.startswith("images/"):
            key = key[len("images/"):]

        entry = manifest.get(key)
        if not entry:
            skipped += 1
            return tag

        if "srcset=" in tag:
            return tag  # already handled

        variants = entry["variants"]
        ordered = sorted(variants.items(), key=lambda kv: int(kv[0]))
        largest = ordered[-1][1]

        start = max(0, match.start() - 900)
        context = text[start:match.start()]
        sizes = sizes_for(context)

        # Strip the closing bracket exactly once, then append attributes, then
        # close once. (Appending with [:-1] after each attribute silently ate
        # the previous attribute's closing quote.)
        body = tag.rstrip()
        if body.endswith("/>"):
            body = body[:-2].rstrip()
        elif body.endswith(">"):
            body = body[:-1].rstrip()

        body = body.replace(f'src="{raw_src}"', f'src="{largest}"', 1)

        srcset = ", ".join(f"{loc} {w}w" for w, loc in ordered)
        body += f' srcset="{srcset}" sizes="{sizes}"'

        if " width=" not in body:
            body += f' width="{entry["width"]}" height="{entry["height"]}"'
        if "decoding=" not in body:
            body += ' decoding="async"'
        if "loading=" not in body:
            body += ' loading="lazy"'

        rewritten += 1
        return body + ">"

    text = IMG_RE.sub(replace_tag, text)

    if text != original and not DRY_RUN:
        path.write_text(text, encoding="utf-8")
    return rewritten, skipped


def main() -> None:
    manifest = build_variants()

    if not DRY_RUN:
        MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"manifest written to {MANIFEST.relative_to(ROOT)}")

    total_rw = 0
    for page in sorted(ROOT.glob("*.html")):
        rw, sk = rewrite_page(page, manifest)
        total_rw += rw
        if rw:
            print(f"  {page.name:24s} rewrote {rw} img tags ({sk} skipped)")

    print(f"\ntotal <img> tags rewritten: {total_rw}")

    if not DRY_RUN and OUT.exists():
        before = sum(
            p.stat().st_size for p in IMAGES.rglob("*")
            if p.is_file() and p.suffix.lower() in SOURCE_EXT and OUT not in p.parents
        )
        after = sum(p.stat().st_size for p in OUT.rglob("*.webp") if p.is_file())
        print(f"original raster total : {before / 1048576:.1f} MB")
        print(f"webp variant total    : {after / 1048576:.1f} MB")


if __name__ == "__main__":
    main()
