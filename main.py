#!/usr/bin/env python3
"""VELMARA — The Floating Isles.

A golden-age travel poster for a place that does not exist, drawn entirely
with the Python standard library. No fonts, no image files, no network:
every shape and every letterform is drawn by hand on a pixel canvas and the
result is written out as a PNG with a small zlib-based encoder.

Run:  python3 main.py
Out:  /output/entry.png  (1024 x 1024, under 1 MiB)
"""

import os
import struct
import zlib

W = 1024
H = 1024
OUT = "/output/entry.png"

# ---------------------------------------------------------------- palette ---
# A tight golden-hour palette: deep teal sky, warm gold sun, cream clouds,
# terracotta rock, pine green, and a red lighthouse accent.
TEAL_DEEP = (16, 62, 76)
TEAL = (32, 112, 128)
TEAL_HAZE = (110, 168, 172)
GOLD = (243, 184, 74)
SUN = (250, 205, 92)
SUN_HALO = (247, 222, 138)
CREAM = (251, 243, 223)
CLOUD_SHADE = (233, 218, 178)
ROCK = (139, 91, 60)
ROCK_DARK = (109, 68, 44)
ROCK_LIT = (168, 116, 78)
GRASS = (63, 122, 94)
PINE = (38, 92, 74)
WHITE = (255, 255, 255)
RED = (199, 75, 53)
WATER = (186, 218, 216)
WATER_DEEP = (140, 188, 190)
INK = (18, 52, 64)


# ------------------------------------------------------------------ canvas --
class Canvas:
    """A plain RGB framebuffer with a few flat-colour drawing helpers."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def rect(self, x0, y0, x1, y1, c):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        for y in range(y0, y1):
            i = (y * self.w + x0) * 3
            self.px[i:i + (x1 - x0) * 3] = bytes(c) * (x1 - x0)

    def hline(self, x0, x1, y, c):
        self.rect(x0, y, x1, y + 1, c)

    def vline(self, x, y0, y1, c):
        self.rect(x, y0, x + 1, y1, c)

    def frame(self, x0, y0, x1, y1, t, c):
        self.rect(x0, y0, x1, y0 + t, c)
        self.rect(x0, y1 - t, x1, y1, c)
        self.rect(x0, y0, x0 + t, y1, c)
        self.rect(x1 - t, y0, x1, y1, c)

    def disc(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            half = int((r * r - dy * dy) ** 0.5)
            self.hline(cx - half, cx + half + 1, cy + dy, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for dy in range(-ry, ry + 1):
            t = 1.0 - (dy * dy) / float(ry * ry)
            half = int(rx * (t ** 0.5)) if t > 0 else 0
            self.hline(cx - half, cx + half + 1, cy + dy, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        """Bresenham line with a square brush of thickness t."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        half = t // 2
        while True:
            self.rect(x - half, y - half, x - half + t, y - half + t, c)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def poly(self, pts, c):
        """Scanline fill of a simple polygon."""
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / float(y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(int(xs[i]), int(xs[i + 1]) + 1, y, c)

    def vgrad(self, y0, y1, top, bottom):
        """Vertical linear gradient between two colours."""
        span = max(1, y1 - y0)
        for y in range(y0, y1):
            f = (y - y0) / span
            c = tuple(int(top[k] + (bottom[k] - top[k]) * f) for k in range(3))
            self.hline(0, self.w, y, c)


def mix(a, b, f):
    return tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3))


# ------------------------------------------------------------- letterforms --
# A hand-built 5x7 bitmap alphabet. Each glyph is seven rows of five cells;
# '#' is ink, '.' is empty. Only the letters the poster needs are defined.
GLYPHS = {
    "A": (" ##  ", "#  # ", "#  # ", "#### ", "#  # ", "#  # ", "#  # "),
    "B": ("#### ", "#  # ", "#  # ", "#### ", "#  # ", "#  # ", "#### "),
    "C": (" ### ", "#    ", "#    ", "#    ", "#    ", "#    ", " ### "),
    "D": ("#### ", "#  # ", "#  # ", "#  # ", "#  # ", "#  # ", "#### "),
    "E": ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"),
    "F": ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "),
    "G": (" ### ", "#    ", "#    ", "# ## ", "#  # ", "#  # ", " ### "),
    "H": ("#  # ", "#  # ", "#  # ", "#### ", "#  # ", "#  # ", "#  # "),
    "I": ("#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"),
    "L": ("#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"),
    "M": ("#  # ", "## ##", "# # #", "# # #", "#  # ", "#  # ", "#  # "),
    "N": ("#  # ", "## # ", "# ## ", "#  ##", "#  # ", "#  # ", "#  # "),
    "O": (" ### ", "#  # ", "#  # ", "#  # ", "#  # ", "#  # ", " ### "),
    "P": ("#### ", "#  # ", "#  # ", "#### ", "#    ", "#    ", "#    "),
    "R": ("#### ", "#  # ", "#  # ", "#### ", "# #  ", "#  # ", "#  # "),
    "S": (" ### ", "#    ", "#    ", " ### ", "   # ", "   # ", "#### "),
    "T": ("#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "),
    "U": ("#  # ", "#  # ", "#  # ", "#  # ", "#  # ", "#  # ", " ### "),
    "V": ("#  # ", "#  # ", "#  # ", "#  # ", "#  # ", " # # ", "  #  "),
    "Y": ("#  # ", "#  # ", " # # ", "  #  ", "  #  ", "  #  ", "  #  "),
    " ": ("     ", "     ", "     ", "     ", "     ", "     ", "     "),
    ".": ("     ", "     ", "     ", "     ", "     ", "     ", "  #  "),
}


def text_width(s, cell):
    """Pixel width of a string at a given cell size (5 cells + 1 gap)."""
    return len(s) * 6 * cell - cell


def draw_text(cv, s, cx, y, cell, colour, shadow=None):
    """Draw a string centred on cx, top edge at y."""
    x = cx - text_width(s, cell) // 2
    for ch in s:
        g = GLYPHS.get(ch.upper(), GLYPHS[" "])
        for r in range(7):
            for col in range(5):
                if g[r][col] == "#":
                    px = x + col * cell
                    py = y + r * cell
                    if shadow is not None:
                        cv.rect(px + cell // 4, py + cell // 4,
                                px + cell, py + cell, shadow)
                    cv.rect(px, py, px + cell, py + cell, colour)
        x += 6 * cell


# ------------------------------------------------------------------ scenes --
def draw_sky(cv):
    # Deep teal at the top melting into warm gold at the horizon.
    cv.vgrad(0, 690, TEAL_DEEP, GOLD)
    # A soft band of pale gold right above the cloud sea.
    cv.vgrad(560, 700, mix(GOLD, SUN_HALO, 0.25), mix(GOLD, CREAM, 0.55))


def draw_sun(cv):
    # Halo, then the sun itself, low and warm on the right.
    cv.disc(790, 250, 104, SUN_HALO)
    cv.disc(790, 250, 92, mix(SUN_HALO, SUN, 0.45))
    cv.disc(790, 250, 76, SUN)
    cv.disc(790, 250, 68, mix(SUN, GOLD, 0.35))


def draw_distant_isles(cv):
    # Hazy silhouettes far off, barely more than colour in the mist.
    cv.poly([(96, 640), (150, 600), (205, 640)], TEAL_HAZE)
    cv.poly([(846, 648), (906, 610), (966, 648)], TEAL_HAZE)
    cv.ellipse(150, 640, 92, 14, TEAL_HAZE)
    cv.ellipse(906, 648, 96, 14, TEAL_HAZE)


def draw_airship(cv):
    # A small cream-and-red airship drifting in from the upper left,
    # kept clear of the tagline above it.
    cx, cy = 176, 356
    cv.ellipse(cx, cy, 80, 26, CREAM)
    cv.ellipse(cx - 50, cy, 30, 26, CREAM)
    cv.poly([(cx + 50, cy - 22), (cx + 84, cy - 38), (cx + 80, cy - 7)], RED)
    cv.poly([(cx + 50, cy + 22), (cx + 84, cy + 38), (cx + 80, cy + 7)], RED)
    cv.rect(cx - 62, cy - 26, cx + 62, cy - 19, RED)
    cv.rect(cx - 16, cy + 24, cx + 22, cy + 40, ROCK_DARK)
    cv.rect(cx - 16, cy + 24, cx + 22, cy + 29, GOLD)
    for wx in range(cx - 54, cx + 54, 20):
        cv.rect(wx, cy - 7, wx + 9, cy + 5, TEAL_DEEP)


def draw_birds(cv):
    # A few distant birds, simple two-stroke wings.
    for (bx, by, s) in [(420, 300, 12), (470, 276, 9), (330, 430, 11),
                        (660, 420, 10), (740, 380, 8)]:
        cv.line(bx - s, by - s // 2, bx, by, INK, 3)
        cv.line(bx, by, bx + s, by - s // 2, INK, 3)


def draw_small_isle(cv):
    # A little isle with three pines, floating low on the left.
    top = 556
    cv.poly([(128, top), (330, top), (306, top + 34), (262, top + 96),
             (236, top + 128), (196, top + 96), (152, top + 34)], ROCK)
    # Lit face on the right, shadow face on the left.
    cv.poly([(229, top), (330, top), (306, top + 34), (262, top + 96),
             (236, top + 128)], ROCK_LIT)
    cv.poly([(128, top), (229, top), (236, top + 128), (196, top + 96),
             (152, top + 34)], ROCK_DARK)
    cv.ellipse(229, top + 2, 102, 12, GRASS)
    # Three pines of different heights.
    for (tx, th) in [(168, 66), (222, 88), (282, 58)]:
        cv.rect(tx - 3, top - 6, tx + 3, top + 4, ROCK_DARK)
        for k in range(3):
            w = 30 - k * 7
            y0 = top - th + k * (th // 3)
            cv.poly([(tx - w, y0 + th // 3), (tx + w, y0 + th // 3),
                     (tx, y0)], PINE)


def draw_main_isle(cv):
    # The hero: a big floating rock, grassy top, lighthouse, waterfall.
    # Rock body — a broad plateau tapering to a point far below.
    body = [(392, 470), (700, 470), (676, 540), (640, 660), (600, 780),
            (560, 862), (528, 862), (492, 780), (440, 660), (408, 540)]
    cv.poly(body, ROCK)
    # Sunlit right face and shaded left face give the rock its volume.
    cv.poly([(548, 470), (700, 470), (676, 540), (640, 660), (600, 780),
             (560, 862), (548, 862)], ROCK_LIT)
    cv.poly([(392, 470), (548, 470), (548, 862), (528, 862), (492, 780),
             (440, 660), (408, 540)], ROCK_DARK)
    # Cracks and ledges.
    cv.line(470, 560, 520, 640, ROCK_DARK, 3)
    cv.line(520, 640, 500, 720, ROCK_DARK, 3)
    cv.line(610, 580, 580, 690, ROCK_DARK, 3)
    cv.line(430, 700, 470, 760, ROCK_DARK, 3)
    # Grassy plateau.
    cv.ellipse(546, 472, 158, 16, GRASS)
    cv.rect(392, 470, 700, 478, GRASS)
    # A tuft of grass and a pine at the plateau's edge.
    cv.poly([(420, 470), (436, 470), (428, 446)], PINE)
    cv.poly([(652, 470), (668, 470), (660, 442)], PINE)

    # Lighthouse: white tower, red bands, gallery and lamp.
    lx = 560
    cv.poly([(lx - 26, 470), (lx + 26, 470), (lx + 18, 352),
             (lx - 18, 352)], WHITE)
    cv.poly([(lx - 23, 436), (lx + 23, 436), (lx + 21, 414),
             (lx - 21, 414)], RED)
    cv.poly([(lx - 20, 392), (lx + 20, 392), (lx + 19, 372),
             (lx - 19, 372)], RED)
    cv.rect(lx - 30, 348, lx + 30, 356, INK)
    cv.rect(lx - 13, 322, lx + 13, 350, GOLD)
    cv.poly([(lx - 16, 322), (lx + 16, 322), (lx, 300)], RED)
    cv.disc(lx, 336, 7, WHITE)
    # The beam, thrown toward the sun: three widening wedges of pale gold.
    cv.poly([(lx + 12, 330), (lx + 12, 344), (822, 282), (822, 252)], SUN_HALO)
    cv.poly([(lx + 12, 332), (lx + 12, 342), (808, 288), (808, 268)], SUN)
    cv.poly([(lx + 12, 334), (lx + 12, 340), (762, 300), (762, 288)],
            mix(SUN, WHITE, 0.4))

    # Waterfall: a bright ribbon pouring off the left rim into the clouds.
    cv.poly([(424, 472), (452, 472), (448, 640), (446, 800), (428, 800),
             (424, 640)], WATER)
    cv.poly([(430, 472), (442, 472), (440, 640), (439, 800), (432, 800),
             (430, 640)], WATER_DEEP)
    cv.ellipse(438, 806, 34, 12, WHITE)
    cv.ellipse(438, 812, 48, 10, CREAM)


def draw_cloud_sea(cv):
    # The sea of clouds the isles float above: a cream base with soft puffs.
    cv.rect(0, 700, W, H, CREAM)
    cv.vgrad(700, 780, mix(GOLD, CREAM, 0.55), CREAM)
    # Shadowed puffs first, bright puffs on top, so the clouds read round.
    puffs = [
        (120, 760, 120, 34, CLOUD_SHADE), (300, 800, 150, 40, CLOUD_SHADE),
        (520, 770, 140, 36, CLOUD_SHADE), (760, 810, 160, 42, CLOUD_SHADE),
        (930, 760, 120, 34, CLOUD_SHADE), (60, 880, 150, 40, CLOUD_SHADE),
        (420, 900, 170, 44, CLOUD_SHADE), (820, 900, 170, 44, CLOUD_SHADE),
    ]
    for (x, y, rx, ry, c) in puffs:
        cv.ellipse(x, y, rx, ry, c)
    bright = [
        (120, 748, 110, 30), (300, 788, 140, 36), (520, 758, 130, 32),
        (760, 798, 150, 38), (930, 748, 110, 30), (200, 900, 150, 38),
        (560, 910, 160, 40), (900, 890, 140, 36),
    ]
    for (x, y, rx, ry) in bright:
        cv.ellipse(x, y, rx, ry, WHITE)
    # A few gold-lit rims where the sun catches the cloud tops.
    for (x, y, rx) in [(120, 722, 90), (520, 732, 100), (900, 724, 90)]:
        cv.ellipse(x, y, rx, 10, mix(GOLD, CREAM, 0.5))


def draw_type(cv):
    # The name, big and cream, set against the deep teal sky.
    draw_text(cv, "VELMARA", 512, 62, 15, CREAM, shadow=TEAL_DEEP)
    # A thin gold rule under the name.
    cv.rect(512 - 190, 178, 512 + 190, 182, GOLD)
    # The tagline, smaller, in cream so it reads over both teal and gold.
    draw_text(cv, "THE FLOATING ISLES", 512, 196, 7, CREAM, shadow=TEAL_DEEP)
    # The footer, dark ink on the cream cloud sea, sized to fit the frame.
    draw_text(cv, "ABOVE THE CLOUDS . BEYOND THE MAP", 512, 950, 4, INK)


def draw_border(cv):
    # A slim double border: dark ink outside, gold inside.
    cv.frame(16, 16, W - 16, H - 16, 5, INK)
    cv.frame(30, 30, W - 30, H - 30, 3, GOLD)


# -------------------------------------------------------------------- png ---
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    cv = Canvas(W, H, TEAL_DEEP)
    draw_sky(cv)
    draw_sun(cv)
    draw_distant_isles(cv)
    draw_airship(cv)
    draw_birds(cv)
    draw_small_isle(cv)
    draw_main_isle(cv)
    draw_cloud_sea(cv)
    draw_type(cv)
    draw_border(cv)
    size = write_png(OUT, cv)
    print(f"wrote {OUT} ({W}x{H}, {size} bytes)")


if __name__ == "__main__":
    main()
