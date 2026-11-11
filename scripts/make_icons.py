#!/usr/bin/env python3
"""
Generate the NiRepurpose app icon set from code (no AI, no stock art, no third-party marks).

Design: a leaf (the project's "shrubbery") inside two circular "repurpose" arrows on a green
rounded-square tile.

Writes:
    assets/nirepurpose.png   1024x1024 (Linux window icon, PyInstaller Linux --icon)
    assets/nirepurpose.ico   16, 24, 32, 48, 64, 128, 256 (Windows exe + window icon)
    assets/nirepurpose.icns  16-1024 incl. @2x (macOS app bundle)

Dev-only tool. Needs Pillow:  python -m pip install pillow
    python scripts/make_icons.py [--out assets] [--preview preview.png]
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
WORK = 2048  # draw large, then downsample for clean edges

TILE_TOP = (52, 190, 118)      # gradient top
TILE_BOTTOM = (16, 102, 62)    # gradient bottom
ARROW = (255, 255, 255)
LEAF = (232, 255, 240)
LEAF_VEIN = (24, 120, 72)

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def _rounded_mask(size: int, radius_ratio: float = 0.225, inset_ratio: float = 0.0) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    inset = round(size * inset_ratio)
    ImageDraw.Draw(mask).rounded_rectangle(
        (inset, inset, size - 1 - inset, size - 1 - inset), radius=round(size * radius_ratio), fill=255
    )
    return mask


def _gradient(size: int, top: tuple, bottom: tuple) -> Image.Image:
    column = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / (size - 1)
        column.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return column.resize((size, size))


def _point(cx: float, cy: float, r: float, degrees: float) -> tuple[float, float]:
    a = math.radians(degrees)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def _arrow_arc(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, start: float, end: float, width: float) -> None:
    """Clockwise arc from start to end (degrees, Pillow convention) with an arrowhead at the end."""
    draw.arc((cx - r, cy - r, cx + r, cy + r), start=start, end=end - 9, fill=ARROW, width=round(width))
    # round cap at the tail
    tx, ty = _point(cx, cy, r - width / 2, start)
    draw.ellipse((tx - width / 2, ty - width / 2, tx + width / 2, ty + width / 2), fill=ARROW)
    # arrowhead: tip ahead along the circle, base across the stroke
    tip = _point(cx, cy, r - width / 2, end + 6)
    base_angle = end - 12
    outer = _point(cx, cy, r - width / 2 + width * 1.15, base_angle)
    inner = _point(cx, cy, r - width / 2 - width * 1.15, base_angle)
    draw.polygon([tip, outer, inner], fill=ARROW)


def _leaf(size: int, cx: float, cy: float, length: float, width: float, angle: float, veins: bool = True) -> Image.Image:
    """Leaf as an RGBA layer: pointed ellipse with a centre vein, rotated by angle degrees."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    steps = 200
    upper, lower = [], []
    for i in range(steps + 1):
        t = i / steps
        x = cx - length / 2 + length * t
        half = (width / 2) * math.sin(math.pi * t) ** 0.85
        upper.append((x, cy - half))
        lower.append((x, cy + half))
    draw.polygon(upper + lower[::-1], fill=LEAF)
    vein = max(2, round(width * 0.07))
    if veins:
        draw.line([(cx - length * 0.42, cy), (cx + length * 0.44, cy)], fill=LEAF_VEIN, width=vein)
        for f in (-0.18, 0.04, 0.24):
            x0 = cx + length * f
            for sign in (-1, 1):
                draw.line([(x0, cy), (x0 + length * 0.12, cy + sign * width * 0.28)], fill=LEAF_VEIN, width=max(1, vein // 2))
    # short stem
    draw.line([(cx - length / 2 - length * 0.10, cy), (cx - length / 2 + length * 0.02, cy)], fill=LEAF, width=vein * 2)
    return layer.rotate(angle, resample=Image.BICUBIC, center=(cx, cy))


def render(size: int = 1024) -> Image.Image:
    s = WORK
    tile_mask = _rounded_mask(s, inset_ratio=0.035)
    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    # soft drop shadow under the tile
    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    shadow.putalpha(tile_mask.point(lambda v: v * 0.35))
    shadow = shadow.transform((s, s), Image.AFFINE, (1, 0, 0, 0, 1, -s * 0.012)).filter(ImageFilter.GaussianBlur(s * 0.012))
    canvas.alpha_composite(shadow)

    tile = _gradient(s, TILE_TOP, TILE_BOTTOM).convert("RGBA")
    tile.putalpha(tile_mask)
    canvas.alpha_composite(tile)

    # Small sizes: bolder arrows, smaller plain leaf, so the mark still reads at 16-32 px.
    small = size <= 32
    glyph = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glyph)
    cx = cy = s / 2
    r = s * (0.33 if small else 0.315)
    w = s * (0.095 if small else 0.062)
    _arrow_arc(draw, cx, cy, r, start=200, end=330, width=w)  # top arc, clockwise
    _arrow_arc(draw, cx, cy, r, start=20, end=150, width=w)   # bottom arc, clockwise
    leaf_len = s * (0.28 if small else 0.30)
    glyph.alpha_composite(_leaf(s, cx, cy, length=leaf_len, width=leaf_len * 0.52, angle=40, veins=not small))
    canvas.alpha_composite(glyph)

    return canvas.resize((size, size), Image.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "assets")
    parser.add_argument("--preview", type=Path, help="also write a preview sheet of all sizes on light and dark")
    args = parser.parse_args()

    master = render(1024)
    args.out.mkdir(parents=True, exist_ok=True)
    master.save(args.out / "nirepurpose.png", optimize=True)
    # Downsample each ICO size from the large render (sharper than letting the writer rescale).
    ico_images = [render(n) if n <= 64 else master.resize((n, n), Image.LANCZOS) for n in ICO_SIZES]
    ico_images[-1].save(args.out / "nirepurpose.ico", format="ICO", sizes=[(n, n) for n in ICO_SIZES],
                        append_images=ico_images[:-1])
    master.save(args.out / "nirepurpose.icns", format="ICNS")
    for name in ("nirepurpose.png", "nirepurpose.ico", "nirepurpose.icns"):
        print(f"wrote {args.out / name} ({(args.out / name).stat().st_size:,} bytes)")

    if args.preview:
        sizes = [16, 32, 48, 64, 128, 256]
        pad = 24
        width = sum(sizes) + pad * (len(sizes) + 1)
        sheet = Image.new("RGBA", (width, (256 + pad * 2) * 2), (0, 0, 0, 255))
        for row, bg in enumerate([(245, 245, 245, 255), (30, 30, 30, 255)]):
            band = Image.new("RGBA", (width, 256 + pad * 2), bg)
            x = pad
            for n in sizes:
                icon = master.resize((n, n), Image.LANCZOS) if n > 64 else render(n)
                band.alpha_composite(icon, (x, pad + 256 - n))
                x += n + pad
            sheet.alpha_composite(band, (0, row * (256 + pad * 2)))
        sheet.convert("RGB").save(args.preview)
        print(f"wrote preview {args.preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
