#!/usr/bin/env python3
"""Generate the site's brand assets:

  favicon.ico           16/32/48 multi-size icon
  favicon.svg           scalable icon
  apple-touch-icon.png  180x180 for iOS home screens
  og-image.jpg          1200x630 social sharing card

Run from the project root:  python tools/build-assets.py
"""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMAGES = ROOT / "images"

BRAND_DARK = (10, 93, 147)     # #0A5D93
BRAND_LIGHT = (10, 189, 227)   # #0ABDE3

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if pathlib.Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rounded_square(size: int, radius_ratio: float = 0.22) -> Image.Image:
    """Brand-coloured rounded square with a white N monogram."""
    scale = 4
    big = size * scale
    icon = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)

    radius = int(big * radius_ratio)
    draw.rounded_rectangle([0, 0, big - 1, big - 1], radius=radius, fill=BRAND_DARK)

    # Accent wedge in the lower-right corner for a little depth.
    draw.rounded_rectangle(
        [big * 0.52, big * 0.62, big - 1, big - 1],
        radius=radius // 2,
        fill=BRAND_LIGHT,
    )

    font = load_font(int(big * 0.62))
    text = "N"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((big - tw) / 2 - bbox[0], (big - th) / 2 - bbox[1] - big * 0.02),
        text,
        font=font,
        fill=(255, 255, 255, 255),
    )

    return icon.resize((size, size), Image.LANCZOS)


def find_source_photo() -> pathlib.Path | None:
    for name in (
        "Yachts/60ft catamaran.jpg",
        "38FT/Cat 38 in water.png",
        "28FT/hunter 28 masirah 1.jpg",
    ):
        candidate = IMAGES / name
        if candidate.exists():
            return candidate
    return None


def build_og_image() -> None:
    width, height = 1200, 630
    photo = find_source_photo()

    if photo:
        card = Image.open(photo).convert("RGB")
        # Cover-crop to the target aspect ratio.
        src_ratio = card.width / card.height
        dst_ratio = width / height
        if src_ratio > dst_ratio:
            new_w = int(card.height * dst_ratio)
            left = (card.width - new_w) // 2
            card = card.crop((left, 0, left + new_w, card.height))
        else:
            new_h = int(card.width / dst_ratio)
            top = int((card.height - new_h) * 0.35)
            card = card.crop((0, top, card.width, top + new_h))
        card = card.resize((width, height), Image.LANCZOS)
    else:
        card = Image.new("RGB", (width, height), BRAND_DARK)

    # Dark scrim, heavier at the bottom so the headline stays legible.
    scrim = Image.new("L", (width, height), 0)
    scrim_draw = ImageDraw.Draw(scrim)
    for y in range(height):
        progress = y / height
        alpha = int(60 + 170 * (progress ** 1.6))
        scrim_draw.line([(0, y), (width, y)], fill=min(alpha, 225))
    card = Image.composite(Image.new("RGB", (width, height), (4, 26, 46)), card, scrim)

    draw = ImageDraw.Draw(card)

    logo_path = IMAGES / "logo-narrow.png"
    if logo_path.exists():
        # The source logo is opaque (white background), so seat it on a white
        # rounded badge instead of trying to knock the background out.
        logo = Image.open(logo_path).convert("RGB")
        target_w = 250
        logo = logo.resize((target_w, max(1, int(logo.height * target_w / logo.width))), Image.LANCZOS)

        pad_x, pad_y = 26, 16
        badge_w = logo.width + pad_x * 2
        badge_h = logo.height + pad_y * 2
        badge = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
        ImageDraw.Draw(badge).rounded_rectangle(
            [0, 0, badge_w - 1, badge_h - 1], radius=14, fill=(255, 255, 255, 255)
        )
        badge.paste(logo, (pad_x, pad_y))
        card.paste(badge, (70, 54), badge)

    headline = "Custom Yacht Construction & OEM Manufacturing"
    subhead = "Engineered in Dubai  \u00b7  Built in Longkou, China  \u00b7  Delivered worldwide"

    draw.text((70, 430), headline, font=load_font(46), fill=(255, 255, 255))
    draw.text((70, 500), subhead, font=load_font(25), fill=(178, 226, 245))

    accent = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(accent).rectangle([70, 494, 190, 497], fill=BRAND_LIGHT + (255,))
    card = Image.alpha_composite(card.convert("RGBA"), accent).convert("RGB")

    out = IMAGES / "og-image.jpg"
    card.save(out, "JPEG", quality=86, optimize=True, progressive=True)
    print(f"  og-image.jpg           {out.stat().st_size / 1024:.0f} KB  {width}x{height}")


def build_white_logo() -> None:
    """Derive a white, transparent-background logo for the dark footer.

    `logo-narrow.png` is an opaque RGB PNG on a white background. The footer
    therefore cannot simply use a CSS `filter: brightness(0) invert(1)` — that
    turns the whole rectangle, background included, into a solid white block and
    the mark vanishes. Building a real alpha channel from luminance instead
    yields crisp white marks on transparency, with the anti-aliased edges of the
    "Dubai" script preserved.

    Outputs `images/logo-narrow-white.png` plus WebP variants in `images/opt/`.
    """
    src = IMAGES / "logo-narrow.png"
    if not src.exists():
        print("  logo-narrow-white     SKIPPED (logo-narrow.png not found)")
        return

    logo = Image.open(src).convert("RGB")
    width, height = logo.size

    # alpha = distance from white, using Rec.601 luma
    luma = [(r * 299 + g * 587 + b * 114) // 1000 for r, g, b in logo.getdata()]
    alpha = Image.new("L", (width, height))
    alpha.putdata([255 - v for v in luma])

    peak = alpha.getextrema()[1]
    if peak:
        alpha = alpha.point(lambda v: min(255, round(v * 255 / peak)))

    white = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    white.putalpha(alpha)

    dest = IMAGES / "logo-narrow-white.png"
    white.save(dest, "PNG", optimize=True)
    print(
        f"  logo-narrow-white.png  {dest.stat().st_size / 1024:.1f} KB  "
        f"{width}x{height}"
    )

    opt = IMAGES / "opt"
    opt.mkdir(exist_ok=True)
    for target in (480, 960, 1019):
        if target > width:
            continue
        scaled = white.resize(
            (target, max(1, round(height * target / width))), Image.LANCZOS
        )
        out = opt / f"logo-narrow-white-png-{target}.webp"
        scaled.save(out, "WEBP", quality=90, method=6)
        print(f"  {out.name:38s} {out.stat().st_size / 1024:.1f} KB  {target}w")


def build_icons() -> None:
    master = rounded_square(512)

    ico_path = ROOT / "favicon.ico"
    master.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print(f"  favicon.ico            {ico_path.stat().st_size / 1024:.1f} KB")

    touch = ROOT / "apple-touch-icon.png"
    rounded_square(180, radius_ratio=0.0).save(touch, "PNG", optimize=True)
    print(f"  apple-touch-icon.png   {touch.stat().st_size / 1024:.1f} KB  180x180")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="NAVIER YACHTS">
  <rect width="64" height="64" rx="14" fill="#0A5D93"/>
  <path d="M34 40h24v10a8 8 0 0 1-8 8H40a8 8 0 0 1-6-18z" fill="#0ABDE3" opacity="0"/>
  <rect x="33" y="39" width="25" height="19" rx="7" fill="#0ABDE3"/>
  <text x="31" y="45" font-family="Arial, Helvetica, sans-serif" font-size="40"
        font-weight="700" fill="#FFFFFF" text-anchor="middle">N</text>
</svg>
"""
    (ROOT / "favicon.svg").write_text(svg, encoding="utf-8")
    print(f"  favicon.svg            {len(svg)} bytes")


def main() -> None:
    print("building brand assets...")
    build_icons()
    build_og_image()
    build_white_logo()
    print("done")


if __name__ == "__main__":
    main()
