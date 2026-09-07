"""
Builds every shipped icon from one square source image.

    python make_icon.py path/to/logo.png

This replaced a script that DREW the old LL monogram size by size, in code,
because a monogram is two thin rectangles and a straight downscale fused them
into a blob at 16px. That reasoning does not carry over: the mark is now a
photographic-looking illustration with no hairline geometry to protect, so the
honest approach is one high-resolution source filtered down with a good kernel.
What survives from the old script is the ICO container written by hand — see
below for why Pillow's own writer is not used.

Outputs, all from the same source:

    static/favicon-64.png        the browser tab (st.set_page_config)
    static/icon-192.png          web app manifest
    static/icon-512.png          web app manifest, and the PWA <link rel=icon>
    static/icon-512-maskable.png manifest, purpose=maskable
    static/apple-touch-icon.png  iOS home screen, 180px
    static/app-icon.ico          the Windows shortcut

The shortcut's icon is `app-icon.ico`, not the `lootledger.ico` this used
to write. Windows caches a shortcut's icon against the pair (file path,
index) and will keep serving the bitmap it already has for that pair even
after the file underneath changes — re-saving the shortcut, bouncing its
IconLocation off another file and back, and ie4uinit -show all failed to
shift it. Writing to a path the shell has never seen has no cache entry to
beat.

The maskable variant is not the same image scaled. Android crops a maskable
icon to whatever shape the launcher wants — a circle, a squircle, a rounded
square — and only the middle 80% is guaranteed to survive. A mark that already
fills its own frame loses its border to that crop, so this one is inset to 80%
on a solid ground and the crop eats the padding instead of the artwork.

CORNERS. The source is a rounded-square mark sitting on a rectangular
ground, so shipped as-is it reads on a desktop as a square tile with a
rounded picture printed on it. The script finds the mark's own frame -- the
box and the corner radius are measured off the image, not guessed -- crops
to it so the art fills the canvas edge to edge, and cuts the corners out to
transparency along that same curve. The mask is drawn at 4x and filtered
down, which is what keeps the curve smooth; drawn at final size it steps
visibly at 32px and below.

Two outputs deliberately keep square, opaque corners:

  apple-touch-icon   iOS applies its OWN mask and expects a full-bleed
                     square. Transparent corners there composite against
                     black, which is a different shape from the one iOS is
                     about to cut.
  icon-512-maskable  the launcher crops it; see above.
"""
from __future__ import annotations

import struct
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).parent
STATIC = HERE / "static"

# The manifest's background_color, so the maskable pad is invisible against the
# ground the launcher composites it on.
GROUND = (7, 9, 12, 255)

PNGS = {
    "favicon-64.png": 64,
    "icon-192.png": 192,
    "icon-512.png": 512,
    "apple-touch-icon.png": 180,
}

# Windows picks 16px for the taskbar and details view and 256px for the large
# preview; the sizes between are what Explorer's other view modes reach for.
ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def load_square(path: Path) -> Image.Image:
    """Open the source and return it square, RGBA, without distorting it.

    A source that is not square is centre-cropped rather than stretched: an
    icon squashed to fit reads as a mistake at every size it is then rendered.
    """
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    if w != h:
        side = min(w, h)
        left, top = (w - side) // 2, (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
    return img


def resized(img: Image.Image, size: int) -> Image.Image:
    return img.resize((size, size), Image.LANCZOS)


def detect_frame(img, thr: int = 130):
    """Find the mark's rounded-square frame: its box and its corner radius.

    Measured, not assumed. The frame is far brighter than the ground it sits
    on, so a luminance threshold finds its edges along the centre lines; the
    radius is then fitted by least squares against the ideal rounded-rect
    outline, x(y) = left + R - sqrt(R^2 - (top + R - y)^2), over rows inside
    the corner. On the shipped mark that fits to an RMS of 0.2px.

    Returns (box, radius), or None when nothing frame-shaped is there -- a
    different source should not be silently cropped to a guess.
    """
    rgb = img.convert("RGB")
    px = rgb.load()
    n = rgb.size[0]

    def lum(x, y):
        r, g, b = px[x, y]
        return (r + g + b) / 3.0

    mid = n // 2
    xs = [x for x in range(n) if lum(x, mid) > thr]
    ys = [y for y in range(n) if lum(mid, y) > thr]
    if not xs or not ys:
        return None
    left, right, top, bottom = xs[0], xs[-1], ys[0], ys[-1]
    if right - left < n * 0.5 or bottom - top < n * 0.5:
        return None

    def first_bright(y):
        for x in range(n):
            if lum(x, y) > thr:
                return x
        return None

    probes = []
    for frac in (0.03, 0.06, 0.09, 0.12, 0.15):
        y = top + int(round(n * frac))
        x = first_bright(y)
        if x is not None:
            probes.append((y, x))
    if len(probes) < 3:
        return None

    best, best_err = None, float("inf")
    for radius in range(int(n * 0.04), int(n * 0.35)):
        err = 0.0
        for y, x_obs in probes:
            dy = (top + radius) - y
            if abs(dy) > radius:
                err = float("inf")
                break
            x_model = left + radius - (radius * radius - dy * dy) ** 0.5
            err += (x_model - x_obs) ** 2
        if err < best_err:
            best_err, best = err, radius
    if best is None:
        return None
    return (left, top, right + 1, bottom + 1), best


def crop_and_round(img, thr: int = 130):
    """Crop to the mark's own frame and cut its corners to transparency.

    Shipped uncropped, the mark reads on a desktop as a square tile with a
    rounded picture printed on it: the ground fills the corners and the icon
    never takes the shape it was drawn as. Cropping to the frame also corrects
    a centring error that is in the source -- the frame sits 108px from the
    left edge and 124px from the right.
    """
    found = detect_frame(img, thr)
    if not found:
        print("! no rounded frame found in the source - shipping it square, "
              "uncropped.")
        return img
    (left, top, right, bottom), radius = found
    art = img.crop((left, top, right, bottom))
    # Square it off the shorter side rather than stretching: the frame is
    # 1815x1811 on the shipped mark, and 4px of scaling is 4px of wrong.
    side = min(art.size)
    ox = (art.size[0] - side) // 2
    oy = (art.size[1] - side) // 2
    art = art.crop((ox, oy, ox + side, oy + side)).convert("RGBA")

    ss = 4
    mask = Image.new("L", (side * ss, side * ss), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, side * ss - 1, side * ss - 1], radius=radius * ss, fill=255)
    mask = mask.resize((side, side), Image.LANCZOS)

    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(art, (0, 0), mask)
    print("  frame at (%d,%d)-(%d,%d), radius %dpx (%.3f of its width) "
          "- cropped and rounded" % (left, top, right, bottom, radius,
                                     radius / float(right - left)))
    return out


def on_ground(img, size: int):
    """Flatten onto the manifest ground, for the outputs that must be opaque."""
    out = Image.new("RGBA", (size, size), GROUND)
    art = resized(img, size)
    out.paste(art, (0, 0), art)
    return out


def maskable(img: Image.Image, size: int = 512, safe: float = 0.8) -> Image.Image:
    """The mark inset into the safe zone, on the manifest's own ground."""
    inner = int(round(size * safe))
    out = Image.new("RGBA", (size, size), GROUND)
    art = resized(img, inner)
    off = (size - inner) // 2
    out.paste(art, (off, off), art)
    return out


def write_ico(img: Image.Image, out: Path, sizes=ICO_SIZES) -> None:
    """Write a multi-resolution ICO by hand.

    Pillow's own ICO writer silently drops entries above 256px and reorders
    what it keeps, and the order matters: Windows walks the directory and takes
    the first entry that satisfies the size it wants, so a badly ordered file
    gets a 256px image scaled down for a 16px slot. Writing the container
    directly is about forty lines and removes the guesswork.

    Every entry is a PNG payload, which Windows has understood since Vista and
    which keeps the alpha channel intact without a mask bitmap.
    """
    payloads = []
    for s in sizes:
        buf = BytesIO()
        resized(img, s).save(buf, format="PNG", optimize=True)
        payloads.append((s, buf.getvalue()))

    # ICONDIR: reserved(0), type(1 = icon), count
    header = struct.pack("<HHH", 0, 1, len(payloads))
    offset = len(header) + 16 * len(payloads)
    entries, blobs = [], []
    for s, data in payloads:
        # 256 is stored as 0 in a single byte — the field is one byte wide and
        # 256 does not fit in it.
        dim = 0 if s >= 256 else s
        entries.append(struct.pack(
            "<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset))
        blobs.append(data)
        offset += len(data)
    out.write_bytes(header + b"".join(entries) + b"".join(blobs))


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[2].strip())
        print("\nPass the source image, e.g.:\n"
              "  python make_icon.py logo.png")
        return 2
    src = Path(sys.argv[1]).expanduser()
    if not src.exists():
        print(f"No such file: {src}")
        return 1

    img = load_square(src)
    w, _ = img.size
    if w < 512:
        print(f"! source is only {w}px — 512 or larger keeps the large "
              f"previews sharp. Continuing anyway.")

    img = crop_and_round(img)

    STATIC.mkdir(exist_ok=True)
    for name, size in PNGS.items():
        # apple-touch-icon stays a full-bleed opaque square: iOS cuts its own
        # mask, and transparent corners there composite against black, which is
        # a different shape from the one iOS is about to apply.
        opaque = (name == "apple-touch-icon.png")
        made = on_ground(img, size) if opaque else resized(img, size)
        made.save(STATIC / name, format="PNG", optimize=True)
        note = "  [opaque, iOS masks it]" if opaque else ""
        print(f"  wrote static/{name}  ({size}x{size}){note}")

    maskable(img).save(STATIC / "icon-512-maskable.png", format="PNG", optimize=True)
    print("  wrote static/icon-512-maskable.png  (512x512, 80% safe zone)")

    write_ico(img, STATIC / "app-icon.ico")
    print(f"  wrote static/app-icon.ico  ({', '.join(str(s) for s in ICO_SIZES)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
