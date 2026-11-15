#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""刷新 products.html「TideMaster — Custom Build Series」四张主图（2026-11，TK-0091）。

背景：该段原图全部来自 tools/optimize-images.py 的老流水线，已知问题三类
  1) 源片本身就是低清（886×629 / 1241×568 / 83 KB 的 2276×1280 / 平滑 3D 渲染），
     再压到 22–48 KB 后放大显示，高清屏明显糊；
  2) 四张比例各不相同（1.65 / 1.78 / 2.18 / 1.41），三张机型卡高度参差；
  3) 尺寸都低于「宽 ≥1600、短边 ≥900」的内规。

本脚本按「同型号、可核验画面」重挑源片，统一裁 16:9，输出 1600/960/480 三档 WebP。
只用 Pillow（不引外部工具），不覆盖 images/ 下的原片，只写 images/opt/。

用法：
    python3 tools/refresh-tidemaster-imagery.py            # 生成
    python3 tools/refresh-tidemaster-imagery.py --dry-run  # 只报尺寸/体积，不落盘

裁切策略：16:9 需要竖向裁切时，在居中 ±15% 范围内搜一个偏移，使「被切掉的上下条带
细节能量」最小，尽量不切掉船体与艉浪。
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from PIL import Image, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "images" / "opt"
# 部分源片存在 TideMasterNew 资产库（同一批自有照片，naiver 仓库只带了降采样副本）
TM = pathlib.Path.home() / "deploy" / "TideMasterNew" / "assets" / "images"

RATIO = 16 / 9
WIDTHS = (1600, 960, 480)
QUALITY = 80
QUALITY_FLOOR = 78
SIZE_LIMIT = 180 * 1024

# (输出目录, 源片, 新文件名前缀, 用途说明)
JOBS = [
    ("38FT", TM / "products/cat-38ft/Cat 38 Launched Port.jpg",
     "38ft-cat-38-launched-port-jpg", "段落主图：CAT 38 已建成、迪拜看船（左舷侧视）"),
    ("18FT", TM / "products/ninja-18ft/Ninja 18 running.png",
     "18ft-ninja-18-running-png", "18ft 机型卡：Ninja 18 航行中"),
    ("28FT", TM / "products/hunter-28ft/Hunter 28 blue port.JPG",
     "28ft-hunter-28-blue-port-jpg", "28ft 机型卡：Hunter 28 蓝船体左舷"),
    ("38FT", TM / "index/Cat 38 in rough sea.png",
     "38ft-cat-38-in-rough-sea-png", "38ft 机型卡：CAT 38 海上航行"),
]


def _row_profile(im: Image.Image, sample_width: int = 320):
    """返回逐行细节能量（用于挑裁切偏移）。"""
    g = im.convert("L").resize(
        (sample_width, max(1, round(im.height * sample_width / im.width))),
        Image.BILINEAR,
    ).filter(ImageFilter.FIND_EDGES)
    px = g.load()
    return [sum(px[x, y] for x in range(g.width)) / g.width for y in range(g.height)]


def pick_crop(im: Image.Image) -> tuple[tuple[int, int, int, int], str]:
    w, h = im.size
    if w / h > RATIO:                                  # 太宽：裁左右，居中
        nw = round(h * RATIO)
        left = (w - nw) // 2
        return (left, 0, left + nw, h), f"左右共裁 {w - nw}px ({100 * (w - nw) / w:.1f}%)，居中"
    nh = round(w / RATIO)                              # 太高：裁上下，能量最小偏移
    cut = h - nh
    if cut <= 0:
        return (0, 0, w, nh if nh <= h else h), "无需裁切（已是 16:9）"
    rows = _row_profile(im)
    total = sum(rows) or 1.0
    lo, hi = int(cut * 0.35), int(cut * 0.65)
    best_top, best_e = lo, None
    for top in range(lo, hi + 1):
        rt = round(top * len(rows) / h)
        rb = round((top + nh) * len(rows) / h)
        energy = (sum(rows[:rt]) + sum(rows[rb:])) / total
        if best_e is None or energy < best_e:
            best_top, best_e = top, energy
    return ((0, best_top, w, best_top + nh),
            f"上下共裁 {cut}px ({100 * cut / h:.1f}%)，偏移 top={best_top}，"
            f"切除条带能量 {100 * (best_e or 0):.1f}%")


def run(dry_run: bool) -> int:
    rows = []
    for outdir, src, prefix, memo in JOBS:
        if not src.exists():
            print(f"  MISSING {src}")
            return 2
        with Image.open(src) as raw:
            raw.load()
            im = raw.convert("RGB")
        box, how = pick_crop(im)
        crop = im.crop(box)
        lines = []
        for width in WIDTHS:
            height = round(crop.height * width / crop.width)
            quality = QUALITY
            while True:
                variant = crop.resize((width, height), Image.LANCZOS)
                dest = OUT / outdir / f"{prefix}-{width}.webp"
                if not dry_run:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    variant.save(dest, "WEBP", quality=quality, method=6)
                    size = dest.stat().st_size
                else:
                    import io
                    buf = io.BytesIO()
                    variant.save(buf, "WEBP", quality=quality, method=6)
                    size = buf.tell()
                if width == WIDTHS[0] and size > SIZE_LIMIT and quality > QUALITY_FLOOR:
                    quality -= 1
                    continue
                break
            lines.append((width, height, size, quality))
        rows.append((src, im.size, how, crop.size, lines, memo, prefix, outdir))

    for src, size, how, csize, lines, memo, prefix, outdir in rows:
        print(f"\n{memo}")
        print(f"  源片 {src.relative_to(pathlib.Path.home()) if str(src).startswith(str(pathlib.Path.home())) else src}")
        print(f"    {size[0]}x{size[1]}  {src.stat().st_size // 1024} KB → {how} → 裁后 {csize[0]}x{csize[1]}")
        for width, height, nbytes, quality in lines:
            flag = "OK" if nbytes <= SIZE_LIMIT else "OVER"
            print(f"    images/opt/{outdir}/{prefix}-{width}.webp  {width}x{height}  "
                  f"{nbytes / 1024:.1f} KB  q={quality}  [{flag}]")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    sys.exit(run(ap.parse_args().dry_run))
