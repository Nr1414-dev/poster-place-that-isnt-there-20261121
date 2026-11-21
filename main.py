"""VELMARA — The Floating Isles.

Entry for make.fun competition the-poster-for-a-place-that-i-2-20261121-0539:
a program that draws one travel poster for a place that does not exist and
writes it to $MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png).

Pure Python 3.13 standard library only (zlib/struct for the PNG writer).
Deterministic: no network, no randomness, no clock, no input of any kind;
every run writes byte-identical output.

The poster is drawn procedurally at 2x supersampling (2048) and downsampled
to 1024x1024. The place name is set with a hand-built geometric stroke font
defined below (grid 12 wide x 16 tall per glyph).
"""

import os
import struct
import zlib
from pathlib import Path

W = 1024          # final width/height
SS = 2            # supersampling factor
S = W * SS        # working canvas size (2048)

# ---------------------------------------------------------------- palette ---
# A limited golden-hour palette, pulled from the hero image itself.
SKY_TOP = (31, 44, 80)       # deep indigo
SKY_MID = (51, 96, 110)      # teal slate
SKY_LOW = (232, 144, 63)     # warm amber near the horizon
HORIZON = (246, 196, 83)     # gold
SUN = (253, 213, 148)        # sun disc: warm gold, not moon-pale
CLOUD_CREAM = (247, 232, 201)
CLOUD_LILAC = (201, 184, 212)
CLOUD_SHADE = (154, 134, 176)
ROCK = (75, 53, 80)
ROCK_LIGHT = (140, 98, 112)
ROCK_DARK = (53, 38, 62)
GRASS = (143, 174, 107)
GRASS_DARK = (110, 140, 82)
FALL = (207, 232, 228)       # waterfall
LIGHTHOUSE = (247, 232, 201)
CORAL = (217, 108, 74)
INK = (34, 49, 92)           # type outline / dark accents
PAPER = (251, 243, 220)      # type face
SHIP = (232, 144, 63)

# ------------------------------------------------------------- raster core --
class Canvas:
    """RGB canvas with slice-based fills (fast in pure Python)."""

    def __init__(self, size):
        self.n = size
        self.buf = bytearray(size * size * 3)

    def _row(self, y):
        return y * self.n * 3

    def hline(self, x0, x1, y, color):
        """Fill one horizontal span [x0, x1) on row y with a solid color."""
        y = int(y)
        if y < 0 or y >= self.n:
            return
        x0 = max(0, int(x0))
        x1 = min(self.n, int(x1))
        if x1 <= x0:
            return
        row = self._row(y)
        span = bytes(color) * (x1 - x0)
        self.buf[row + x0 * 3: row + x1 * 3] = span

    def vgrad(self, y0, y1, stops):
        """Vertical gradient between y0 and y1; stops = [(pos0..1, color)]."""
        y0 = max(0, int(y0))
        y1 = min(self.n, int(y1))
        if y1 <= y0:
            return
        span = y1 - y0
        for y in range(y0, y1):
            t = (y - y0) / span
            c = grad_color(stops, t)
            self.hline(0, self.n, y, c)

    def ellipse(self, cx, cy, rx, ry, color):
        """Filled ellipse (scanline spans)."""
        rx = int(rx)
        ry = int(ry)
        for dy in range(-ry, ry + 1):
            y = int(cy) + dy
            if y < 0 or y >= self.n:
                continue
            f = 1.0 - (dy * dy) / float(ry * ry)
            if f <= 0:
                continue
            hw = int(rx * (f ** 0.5))
            self.hline(cx - hw, cx + hw + 1, y, color)

    def disc(self, cx, cy, r, color):
        self.ellipse(cx, cy, r, r, color)

    def poly(self, pts, color):
        """Filled polygon (even-odd scanline fill)."""
        pts = [(float(x), float(y)) for x, y in pts]
        ymin = max(0, int(min(y for _, y in pts)))
        ymax = min(self.n - 1, int(max(y for _, y in pts)))
        edges = []
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            if y1 == y2:
                continue
            edges.append((x1, y1, x2, y2))
        for y in range(ymin, ymax + 1):
            yc = y + 0.5
            xs = []
            for x1, y1, x2, y2 in edges:
                if (y1 <= yc < y2) or (y2 <= yc < y1):
                    xs.append(x1 + (yc - y1) * (x2 - x1) / (y2 - y1))
            if len(xs) < 2:
                continue
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(xs[i], xs[i + 1] + 1, y, color)

    def radial_glow(self, cx, cy, r_max, color):
        """Smooth radial glow: per-pixel falloff (no ring banding)."""
        cx = int(cx)
        cy = int(cy)
        r = int(r_max)
        buf = self.buf
        n = self.n
        cr, cg, cb = color
        for y in range(max(0, cy - r), min(n, cy + r + 1)):
            dy = y - cy
            row = y * n * 3
            for x in range(max(0, cx - r), min(n, cx + r + 1)):
                dx = x - cx
                d2 = dx * dx + dy * dy
                if d2 >= r * r:
                    continue
                d = (d2 ** 0.5) / r
                a = (1.0 - d) * (1.0 - d)
                i = row + x * 3
                buf[i] = int(buf[i] + (cr - buf[i]) * a)
                buf[i + 1] = int(buf[i + 1] + (cg - buf[i + 1]) * a)
                buf[i + 2] = int(buf[i + 2] + (cb - buf[i + 2]) * a)

    def thick_seg(self, x1, y1, x2, y2, w, color):
        """Thick line segment with round caps (quad + endpoint discs)."""
        dx, dy = x2 - x1, y2 - y1
        ln = (dx * dx + dy * dy) ** 0.5
        r = w / 2.0
        if ln < 1e-6:
            self.disc(x1, y1, r, color)
            return
        nx, ny = -dy / ln * r, dx / ln * r
        self.poly([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
                   (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)], color)
        self.disc(x1, y1, r, color)
        self.disc(x2, y2, r, color)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def grad_color(stops, t):
    """stops: sorted [(pos, color)]; returns interpolated color at t."""
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(1, len(stops)):
        if t <= stops[i][0]:
            p0, c0 = stops[i - 1]
            p1, c1 = stops[i]
            f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
            return lerp(c0, c1, f)
    return stops[-1][1]


# ------------------------------------------------------------- stroke font --
# Geometric single-stroke capitals on a 12 (wide) x 16 (tall) grid, y down.
GLYPHS = {
    "A": [[(1, 16), (6, 0), (11, 16)], [(3.8, 10), (8.2, 10)]],
    "B": [[(1, 0), (1, 16)],
          [(1, 0), (7, 0), (10.5, 2.5), (10.5, 5), (7, 7.5), (1, 7.5)],
          [(1, 7.5), (7, 7.5), (10.5, 10), (10.5, 13.5), (7, 16), (1, 16)]],
    "C": [[(11, 3.5), (8, 0), (3.5, 0), (1, 3), (1, 13), (3.5, 16), (8, 16), (11, 12.5)]],
    "D": [[(1, 0), (1, 16)], [(1, 0), (7.5, 0), (11, 3.5), (11, 12.5), (7.5, 16), (1, 16)]],
    "E": [[(1, 0), (1, 16)], [(1, 0), (11, 0)], [(1, 8), (8, 8)], [(1, 16), (11, 16)]],
    "F": [[(1, 0), (1, 16)], [(1, 0), (11, 0)], [(1, 8), (8, 8)]],
    "G": [[(11, 3.5), (8, 0), (3.5, 0), (1, 3), (1, 13), (3.5, 16), (8, 16),
           (11, 12.5), (11, 8), (6.5, 8)]],
    "H": [[(1, 0), (1, 16)], [(11, 0), (11, 16)], [(1, 8), (11, 8)]],
    "I": [[(1, 0), (11, 0)], [(6, 0), (6, 16)], [(1, 16), (11, 16)]],
    "L": [[(1, 0), (1, 16)], [(1, 16), (11, 16)]],
    "M": [[(1, 16), (1, 0), (6, 8.5), (11, 0), (11, 16)]],
    "N": [[(1, 16), (1, 0), (11, 16), (11, 0)]],
    "O": [[(4, 0), (8, 0), (11, 3.5), (11, 12.5), (8, 16), (4, 16),
           (1, 12.5), (1, 3.5), (4, 0)]],
    "P": [[(1, 0), (1, 16)],
          [(1, 0), (7, 0), (10.5, 2.5), (10.5, 5), (7, 7.5), (1, 7.5)]],
    "R": [[(1, 0), (1, 16)],
          [(1, 0), (7, 0), (10.5, 2.5), (10.5, 5), (7, 7.5), (1, 7.5)],
          [(6.5, 7.5), (11, 16)]],
    "S": [[(10, 3.5), (8, 0), (4, 0), (1.5, 2), (1.5, 5.5), (4, 7.5),
           (8, 8.5), (10.5, 11), (10.5, 14), (8, 16), (4, 16), (1.5, 13.5)]],
    "T": [[(1, 0), (11, 0)], [(6, 0), (6, 16)]],
    "U": [[(1, 0), (1, 12.5), (3.5, 16), (8.5, 16), (11, 12.5), (11, 0)]],
    "V": [[(1, 0), (6, 16), (11, 0)]],
    "W": [[(1, 0), (3, 16), (6, 8), (9, 16), (11, 0)]],
    "Y": [[(1, 0), (6, 8), (11, 0)], [(6, 8), (6, 16)]],
}
ADVANCE = 12.0   # grid units per glyph
SPACE_ADVANCE = 7.0


def text_width(text, spacing):
    w = 0.0
    for ch in text:
        if ch == " ":
            w += SPACE_ADVANCE + spacing
        else:
            w += ADVANCE + spacing
    return w - spacing if text else 0.0


def draw_text(cv, text, cx, top, cap_h, stroke, color, spacing=1.0):
    """Draw centred text; top = y of cap top, cap_h = cap height (px, canvas units)."""
    unit = cap_h / 16.0
    total = text_width(text, spacing) * unit
    x = cx - total / 2.0
    for ch in text:
        if ch == " ":
            x += (SPACE_ADVANCE + spacing) * unit
            continue
        if ch == "·":
            cv.disc(x + 6 * unit, top + 8 * unit, 1.6 * unit, color)
            x += (ADVANCE + spacing) * unit
            continue
        for stroke_pts in GLYPHS[ch]:
            pts = [(x + px * unit, top + py * unit) for px, py in stroke_pts]
            for i in range(len(pts) - 1):
                cv.thick_seg(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                             stroke, color)
            # round joins: disc at every interior vertex
            for px, py in pts[1:-1]:
                cv.disc(px, py, stroke / 2.0, color)
        x += (ADVANCE + spacing) * unit


def draw_text_outlined(cv, text, cx, top, cap_h, stroke, face, outline,
                       spacing=1.0, outline_w=None):
    ow = outline_w if outline_w is not None else stroke * 0.55
    draw_text(cv, text, cx, top, cap_h, stroke + 2 * ow, outline, spacing)
    draw_text(cv, text, cx, top, cap_h, stroke, face, spacing)


# ------------------------------------------------------------------- scene --
def cloud(cv, cx, cy, w, h, top_color, base_color):
    """A soft flat cloud: stacked ellipses, lighter on top."""
    cv.ellipse(cx, cy + h * 0.28, w * 0.52, h * 0.62, base_color)
    cv.ellipse(cx - w * 0.30, cy + h * 0.32, w * 0.30, h * 0.45, base_color)
    cv.ellipse(cx + w * 0.30, cy + h * 0.32, w * 0.30, h * 0.45, base_color)
    cv.ellipse(cx, cy, w * 0.50, h * 0.58, top_color)
    cv.ellipse(cx - w * 0.28, cy + h * 0.10, w * 0.27, h * 0.42, top_color)
    cv.ellipse(cx + w * 0.28, cy + h * 0.10, w * 0.27, h * 0.42, top_color)


def pine(cv, x, y, h, color):
    """A small flat pine tree, base at (x, y), height h."""
    cv.poly([(x - h * 0.30, y - h * 0.55), (x, y - h), (x + h * 0.30, y - h * 0.55)], color)
    cv.poly([(x - h * 0.36, y - h * 0.30), (x, y - h * 0.72), (x + h * 0.36, y - h * 0.30)], color)
    cv.poly([(x - h * 0.42, y), (x, y - h * 0.45), (x + h * 0.42, y)], color)
    cv.hline(x - h * 0.05, x + h * 0.05, y - h * 0.02, color)


def draw_poster(cv):
    n = cv.n
    u = n / 1024.0  # scale factor: design in 1024 space

    # --- sky: deep indigo down to gold at the horizon -------------------
    cv.vgrad(0, n, [
        (0.00, SKY_TOP),
        (0.38, SKY_MID),
        (0.62, SKY_LOW),
        (0.78, HORIZON),
        (1.00, HORIZON),
    ])

    # --- sun + smooth glow ----------------------------------------------
    sx, sy, sr = 712 * u, 452 * u, 88 * u
    cv.radial_glow(sx, sy, sr * 1.9, lerp(SUN, HORIZON, 0.45))
    cv.disc(sx, sy, sr, SUN)

    # --- distant hazy isles (low, flat silhouettes) ----------------------
    cv.poly([(140 * u, 432 * u), (180 * u, 412 * u), (232 * u, 432 * u),
             (218 * u, 450 * u), (152 * u, 450 * u)], CLOUD_LILAC)
    cv.poly([(852 * u, 374 * u), (888 * u, 356 * u), (926 * u, 374 * u),
             (912 * u, 390 * u), (866 * u, 390 * u)], CLOUD_LILAC)
    cv.poly([(946 * u, 432 * u), (970 * u, 418 * u), (994 * u, 432 * u),
             (986 * u, 446 * u), (956 * u, 446 * u)], CLOUD_SHADE)
    cv.poly([(282 * u, 486 * u), (312 * u, 470 * u), (344 * u, 486 * u),
             (332 * u, 500 * u), (294 * u, 500 * u)], CLOUD_LILAC)

    # --- airship, upper left --------------------------------------------
    ax, ay = 185 * u, 330 * u
    cv.ellipse(ax, ay, 74 * u, 24 * u, SHIP)
    cv.ellipse(ax, ay - 5 * u, 74 * u, 18 * u, lerp(SHIP, SUN, 0.35))
    cv.poly([(ax + 50 * u, ay - 7 * u), (ax + 74 * u, ay - 24 * u),
             (ax + 74 * u, ay - 2 * u)], CORAL)
    cv.poly([(ax - 10 * u, ay + 22 * u), (ax + 26 * u, ay + 22 * u),
             (ax + 21 * u, ay + 36 * u), (ax - 5 * u, ay + 36 * u)], ROCK_DARK)
    cv.hline(ax - 62 * u, ax - 36 * u, ay - 2 * u, PAPER)

    # --- birds ------------------------------------------------------------
    for bx, by, s in [(845, 300, 1.0), (880, 322, 0.8), (812, 330, 0.7)]:
        bx, by = bx * u, by * u
        cv.thick_seg(bx - 9 * s * u, by, bx, by - 6 * s * u, 3.2 * u, INK)
        cv.thick_seg(bx, by - 6 * s * u, bx + 9 * s * u, by, 3.2 * u, INK)

    # --- main floating isle ---------------------------------------------
    # rock body: broad plateau tapering to a point below
    cv.poly([
        (210 * u, 600 * u), (650 * u, 600 * u), (610 * u, 660 * u),
        (560 * u, 730 * u), (470 * u, 800 * u), (430 * u, 838 * u),
        (392 * u, 800 * u), (330 * u, 724 * u), (268 * u, 660 * u),
    ], ROCK)
    # sunlit cliff face (right side)
    cv.poly([
        (470 * u, 600 * u), (650 * u, 600 * u), (610 * u, 660 * u),
        (560 * u, 730 * u), (470 * u, 800 * u), (430 * u, 838 * u),
        (452 * u, 760 * u), (470 * u, 690 * u),
    ], ROCK_LIGHT)
    # grassy top
    cv.ellipse(430 * u, 598 * u, 222 * u, 26 * u, GRASS)
    cv.ellipse(430 * u, 592 * u, 222 * u, 20 * u, lerp(GRASS, SUN, 0.25))
    # grass tufts
    for gx in (260, 330, 520, 580):
        gx = gx * u
        cv.poly([(gx, 596 * u), (gx + 8 * u, 578 * u), (gx + 16 * u, 596 * u)],
                GRASS_DARK)

    # waterfall pouring off the right edge into the clouds
    cv.poly([(596 * u, 606 * u), (628 * u, 606 * u), (622 * u, 700 * u),
             (612 * u, 792 * u), (604 * u, 792 * u), (600 * u, 700 * u)], FALL)
    cv.hline(602 * u, 624 * u, 640 * u, PAPER)
    cv.hline(604 * u, 618 * u, 700 * u, PAPER)
    # splash puff where the waterfall meets the clouds
    cloud(cv, 610 * u, 800 * u, 110 * u, 26 * u, CLOUD_CREAM, CLOUD_LILAC)

    # --- lighthouse on the main isle ------------------------------------
    lx, lbase = 520 * u, 600 * u
    cv.poly([(lx - 16 * u, lbase), (lx - 11 * u, lbase - 92 * u),
             (lx + 11 * u, lbase - 92 * u), (lx + 16 * u, lbase)], LIGHTHOUSE)
    cv.poly([(lx - 20 * u, lbase - 92 * u), (lx + 20 * u, lbase - 92 * u),
             (lx + 14 * u, lbase - 104 * u), (lx - 14 * u, lbase - 104 * u)], CORAL)
    cv.poly([(lx - 9 * u, lbase - 104 * u), (lx + 9 * u, lbase - 104 * u),
             (lx + 6 * u, lbase - 120 * u), (lx - 6 * u, lbase - 120 * u)], INK)
    cv.disc(lx, lbase - 112 * u, 7 * u, SUN)
    # light beam toward the sun
    cv.poly([(lx + 8 * u, lbase - 116 * u), (lx + 8 * u, lbase - 106 * u),
             (lx + 150 * u, lbase - 74 * u), (lx + 150 * u, lbase - 88 * u)],
            lerp(SUN, HORIZON, 0.25))

    # --- small isle with pines, right ------------------------------------
    cv.poly([(760 * u, 636 * u), (905 * u, 636 * u), (880 * u, 680 * u),
             (845 * u, 726 * u), (828 * u, 752 * u), (812 * u, 724 * u),
             (785 * u, 678 * u)], ROCK)
    cv.ellipse(832 * u, 634 * u, 74 * u, 12 * u, GRASS)
    pine(cv, 800 * u, 634 * u, 34 * u, GRASS_DARK)
    pine(cv, 832 * u, 632 * u, 44 * u, GRASS_DARK)
    pine(cv, 864 * u, 634 * u, 30 * u, GRASS_DARK)

    # --- sea of clouds ----------------------------------------------------
    cloud(cv, 200 * u, 880 * u, 420 * u, 90 * u, CLOUD_CREAM, CLOUD_LILAC)
    cloud(cv, 830 * u, 900 * u, 460 * u, 100 * u, CLOUD_CREAM, CLOUD_LILAC)
    cloud(cv, 520 * u, 950 * u, 560 * u, 110 * u, CLOUD_CREAM, CLOUD_SHADE)
    cloud(cv, 120 * u, 990 * u, 300 * u, 70 * u, CLOUD_LILAC, CLOUD_SHADE)
    cloud(cv, 940 * u, 985 * u, 300 * u, 70 * u, CLOUD_LILAC, CLOUD_SHADE)
    # cloud puffs hugging the isles' points
    cloud(cv, 430 * u, 830 * u, 220 * u, 44 * u, CLOUD_CREAM, CLOUD_LILAC)
    cloud(cv, 828 * u, 748 * u, 150 * u, 34 * u, CLOUD_CREAM, CLOUD_LILAC)

    # --- double border -----------------------------------------------------
    b1, b2 = 26 * u, 36 * u
    for inset, wdt in ((b1, 3 * u), (b2, 1.5 * u)):
        cv.hline(inset, n - inset, inset, CLOUD_CREAM)
        cv.hline(inset, n - inset, n - inset - wdt, CLOUD_CREAM)
        for y in range(int(inset), int(n - inset)):
            cv.hline(inset, inset + wdt, y, CLOUD_CREAM)
            cv.hline(n - inset - wdt, n - inset, y, CLOUD_CREAM)

    # --- type: name, tagline, footer ---------------------------------------
    cx = n / 2.0
    draw_text_outlined(cv, "VELMARA", cx, 118 * u, 128 * u, 15 * u,
                       PAPER, INK, spacing=3.0)
    # tagline with flanking rules
    ty = 268 * u
    draw_text(cv, "THE FLOATING ISLES", cx, ty, 34 * u, 5.5 * u, PAPER, spacing=4.0)
    tw = text_width("THE FLOATING ISLES", 4.0) * (34 * u / 16.0)
    cv.hline(cx - tw / 2 - 130 * u, cx - tw / 2 - 30 * u, ty + 17 * u, PAPER)
    cv.hline(cx + tw / 2 + 30 * u, cx + tw / 2 + 130 * u, ty + 17 * u, PAPER)
    draw_text(cv, "ABOVE THE CLOUDS · BEYOND THE MAP", cx, 962 * u, 22 * u,
              3.6 * u, INK, spacing=3.0)


# ------------------------------------------------------------------- png ---
def write_png(path, rgb, size):
    """Encode an RGB bytearray as a PNG (filter Up per row, zlib level 9)."""
    w = h = size
    raw = bytearray()
    prev = bytes(w * 3)
    for y in range(h):
        row = bytes(rgb[y * w * 3:(y + 1) * w * 3])
        up = bytes((a - b) & 0xFF for a, b in zip(row, prev))
        raw.append(2)  # filter: Up
        raw += up
        prev = row
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    Path(path).write_bytes(png)
    return len(png)


def downsample(src, size):
    """Box-average a (2*size) RGB buffer down to size x size."""
    big = size * SS
    out = bytearray(size * size * 3)
    for y in range(size):
        r0 = (2 * y) * big * 3
        r1 = (2 * y + 1) * big * 3
        o = y * size * 3
        for x in range(size):
            i0 = r0 + (2 * x) * 3
            i1 = r1 + (2 * x) * 3
            for k in range(3):
                out[o + x * 3 + k] = (
                    src[i0 + k] + src[i0 + 3 + k] + src[i1 + k] + src[i1 + 3 + k]
                ) // 4
    return out


def main():
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    cv = Canvas(S)
    draw_poster(cv)
    rgb = downsample(cv.buf, W)
    nbytes = write_png(out_dir / "entry.png", rgb, W)
    print(f"wrote {out_dir / 'entry.png'} ({W}x{W}, {nbytes} bytes)")


if __name__ == "__main__":
    main()
