"""
Builds `static/lootledger.ico` — the LL monogram, for the Windows shortcut.

Why this is not one PNG handed to Pillow with a `sizes=` list: that path renders
the mark once and downsamples it for every entry, and the monogram does not
survive that. At 16 pixels the gap between the two L's is under one pixel wide,
so a straight downscale fuses them into an amber blob with a grey seam. Windows
picks the 16px entry for the taskbar and for details view, which is where a
desktop icon is looked at most.

So every size is drawn on its own. The geometry is expressed as fractions of the
canvas, measured off `static/icon-512.png` so this matches the shipped mark
exactly rather than approximating it, and each rectangle is then rounded to whole
pixels AT THE TARGET SIZE before anything is drawn. Rounding first is the whole
trick: the stems and feet land on exact pixel boundaries, so they come out sharp
instead of smeared across two columns at half opacity. Drawing happens at 8x and
is filtered back down, which keeps the rounded corner smooth while those snapped
edges stay crisp — supersampling for the curve, pixel-snapping for the glyph.

Small sizes also get a floor applied: a stem is never thinner than 2px and the
gap between the letters never closes below 1px, because below that the mark stops
being two letters and there is no point in it at all.

Run:  python make_icon.py
"""
from __future__ import annotations

import struct
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).parent
OUT = HERE / "static" / "lootledger.ico"

VOID = (7, 9, 12, 255)        # --void, dark mode
AMBER = (255, 179, 0, 255)    # --amber, dark mode

# Fractions of the canvas, measured from static/icon-512.png:
#   corner radius 73        glyph x 103..408, y 138..373
#   stems 55 wide at x=103 and x=270, feet 139 wide, foot top at y=320
RADIUS = 73 / 512
GLYPH_X = 103 / 512
STEM_W = 55 / 512
RIGHT_X = 270 / 512
GLYPH_TOP = 138 / 512
GLYPH_BOT = 374 / 512
FOOT_TOP = 320 / 512
FOOT_W = 139 / 512

SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
SS = 8   # supersample factor


def render(size: int) -> Image.Image:
    """One icon entry, drawn for this size rather than scaled down to it."""
    # --- lay the mark out in whole target pixels first ---
    x0 = round(GLYPH_X * size)
    stem = max(2, round(STEM_W * size))
    foot = max(stem + 1, round(FOOT_W * size))
    top = round(GLYPH_TOP * size)
    bot = round(GLYPH_BOT * size)
    foot_top = round(FOOT_TOP * size)
    rx = round(RIGHT_X * size)

    # Keep the letters apart. Without this the left foot grows into the right
    # stem at 16 and 20px and the mark reads as one wide glyph.
    if rx <= x0 + foot:
        rx = x0 + foot + 1
    # ...and keep the whole thing on the canvas after that nudge.
    overflow = (rx + foot) - (size - x0)
    if overflow > 0:
        x0 = max(1, x0 - overflow)
        rx -= overflow

    # A foot only reads as a foot if it is at least a pixel tall.
    if bot - foot_top < 1:
        foot_top = bot - 1

    img = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size * SS - 1, size * SS - 1],
                        radius=RADIUS * size * SS, fill=VOID)
    for left in (x0, rx):
        # stem, then foot — both on target-pixel boundaries, scaled up to draw
        d.rectangle([left * SS, top * SS,
                     (left + stem) * SS - 1, bot * SS - 1], fill=AMBER)
        d.rectangle([left * SS, foot_top * SS,
                     (left + foot) * SS - 1, bot * SS - 1], fill=AMBER)
    return img.resize((size, size), Image.LANCZOS)


def write_ico(images: list[Image.Image], path: Path) -> None:
    """Assemble the .ico by hand.

    Pillow's own ICO writer re-derives every entry from a single image, which is
    exactly what this file exists to avoid. The container is simple enough to
    write directly: a header, one 16-byte directory entry per size, then the
    payloads. Each payload is a PNG — Windows has accepted PNG-compressed
    entries since Vista, and it keeps the 256px entry from costing 256KB as raw
    BMP would.
    """
    payloads = []
    for im in images:
        buf = BytesIO()
        im.save(buf, format="PNG", optimize=True)
        payloads.append(buf.getvalue())

    header = struct.pack("<HHH", 0, 1, len(images))   # reserved, type=icon, count
    offset = len(header) + 16 * len(images)
    entries = b""
    for im, data in zip(images, payloads):
        w = 0 if im.width >= 256 else im.width       # 0 encodes 256
        h = 0 if im.height >= 256 else im.height
        entries += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), offset)
        offset += len(data)

    path.write_bytes(header + entries + b"".join(payloads))


def main() -> None:
    images = [render(s) for s in SIZES]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    write_ico(images, OUT)
    print(f"wrote {OUT}  ({OUT.stat().st_size:,} bytes)")
    print("sizes:", ", ".join(f"{s}x{s}" for s in SIZES))


if __name__ == "__main__":
    main()
