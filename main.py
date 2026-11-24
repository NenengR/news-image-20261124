#!/usr/bin/env python3
"""News Image 20261124: sum up Tuesday 24 November 2026 world news in one image.

Writes /output/entry.png (1024x1024, under 1 MiB, fully deterministic).
Pure Python standard library only, no network, no external assets.
"""
import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 characters, '#' = pixel on, '.' = pixel off.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    '$': ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
}

# ---------------------------------------------------------------- colours
NAVY = (26, 42, 74)
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
DARK = (40, 40, 40)
BLUE = (46, 134, 193)
GREEN = (39, 174, 96)
DARKGREEN = (27, 94, 32)
YELLOW = (241, 196, 15)
ORANGE = (230, 126, 34)
RED = (192, 57, 43)
GREY = (120, 120, 120)
LIGHTGREY = (200, 200, 200)
BROWN = (146, 94, 48)
SAND = (210, 180, 120)

PANELS = [
    # bg colour, line1, line2
    ((216, 239, 216), "COP31: NO DEAL ON", "FOSSIL FUELS"),
    ((205, 228, 245), "SEA DRONE HITS", "RUSSIAN CORVETTE"),
    ((223, 242, 223), "HUANG RETURNS,", "NVIDIA UP $1T"),
    ((191, 217, 242), "25 SEAFARERS", "KILLED AT HORMUZ"),
    ((245, 245, 245), "VERSTAPPEN WINS", "LAS VEGAS GP"),
    ((242, 227, 198), "6.5 QUAKE HITS", "VANUATU"),
]

# ---------------------------------------------------------------- framebuffer
fb = bytearray(W * H * 3)


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        fb[i] = c[0]
        fb[i + 1] = c[1]
        fb[i + 2] = c[2]


def rect(x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(x, y, c)


def circle(cx, cy, r, c):
    for y in range(cy - r, cy + r + 1):
        dy = y - cy
        dx = int((r * r - dy * dy) ** 0.5)
        for x in range(cx - dx, cx + dx + 1):
            put(x, y, c)


def line(x0, y0, x1, y1, c, w=1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        for ox in range(w):
            for oy in range(w):
                put(x + ox, y + oy, c)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def triangle(x0, y0, x1, y1, x2, y2, c):
    # Filled triangle via scanline: sort vertices by y.
    pts = sorted([(x0, y0), (x1, y1), (x2, y2)], key=lambda p: p[1])
    (ax, ay), (bx, by), (cx, cy) = pts
    if ay == cy:
        return
    for y in range(ay, cy + 1):
        if y < by:
            if by == ay:
                xa = ax
            else:
                xa = ax + (bx - ax) * (y - ay) / (by - ay)
            if cy == ay:
                xb = ax
            else:
                xb = ax + (cx - ax) * (y - ay) / (cy - ay)
        else:
            if cy == by:
                xa = bx
            else:
                xa = bx + (cx - bx) * (y - by) / (cy - by)
            if cy == ay:
                xb = ax
            else:
                xb = ax + (cx - ax) * (y - ay) / (cy - ay)
        x0i, x1i = int(min(xa, xb)), int(max(xa, xb))
        for x in range(x0i, x1i + 1):
            put(x, y, c)


def text(s, x, y, scale, c):
    for ci, ch in enumerate(s):
        g = FONT.get(ch, FONT[' '])
        ox = x + ci * (6 * scale)
        for r in range(7):
            row = g[r]
            for cc in range(5):
                if row[cc] == '1':
                    for dy in range(scale):
                        for dx in range(scale):
                            put(ox + cc * scale + dx, y + r * scale + dy, c)


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def text_centered(s, cx, y, scale, c):
    x = cx - text_width(s, scale) // 2
    text(s, x, y, scale, c)


# ---------------------------------------------------------------- pictograms
# Each takes the panel origin (px, py). Panel is 512x312; pictogram zone
# roughly y py+14 .. py+195, headline lines at py+210 and py+250.

def pic_cop31(px, py):
    # Sun top right, globe centre.
    for i in range(8):
        ang = i * 3.14159 / 4
        x0 = px + 400 + int(34 * math.cos(ang))
        y0 = py + 52 + int(34 * math.sin(ang))
        x1 = px + 400 + int(48 * math.cos(ang))
        y1 = py + 52 + int(48 * math.sin(ang))
        line(x0, y0, x1, y1, YELLOW, 4)
    circle(px + 400, py + 52, 26, YELLOW)
    circle(px + 256, py + 118, 72, BLUE)
    circle(px + 228, py + 96, 26, GREEN)
    circle(px + 286, py + 140, 30, GREEN)
    circle(px + 268, py + 82, 16, GREEN)
    circle(px + 222, py + 150, 14, GREEN)


def pic_merkury(px, py):
    # Sea, ship hull + superstructure, flames above.
    rect(px + 30, py + 150, px + 482, py + 195, BLUE)
    # hull (trapezoid via two triangles + rect)
    triangle(px + 150, py + 118, px + 360, py + 118, px + 330, py + 152, GREY)
    rect(px + 150, py + 118, px + 360, py + 152, GREY)
    triangle(px + 150, py + 118, px + 150, py + 152, px + 178, py + 152, GREY)
    rect(px + 220, py + 84, px + 300, py + 118, WHITE)
    line(px + 258, py + 58, px + 258, py + 84, DARK, 4)
    # flames
    triangle(px + 210, py + 84, px + 232, py + 84, px + 221, py + 44, ORANGE)
    triangle(px + 250, py + 84, px + 276, py + 84, px + 263, py + 36, RED)
    triangle(px + 290, py + 84, px + 310, py + 84, px + 300, py + 52, ORANGE)
    # smoke
    circle(px + 221, py + 34, 10, LIGHTGREY)
    circle(px + 263, py + 26, 12, LIGHTGREY)


def pic_nvidia(px, py):
    # Chip with pins, rising arrow.
    rect(px + 196, py + 62, px + 316, py + 182, DARKGREEN)
    rect(px + 216, py + 82, px + 296, py + 162, (46, 125, 50))
    rect(px + 236, py + 102, px + 276, py + 142, (165, 214, 167))
    for i in range(4):
        y = py + 78 + i * 30
        rect(px + 176, y, px + 195, y + 12, DARKGREEN)
        rect(px + 317, y, px + 336, y + 12, DARKGREEN)
    # rising arrow polyline
    line(px + 150, py + 190, px + 220, py + 130, GREEN, 6)
    line(px + 220, py + 130, px + 290, py + 150, GREEN, 6)
    line(px + 290, py + 150, px + 370, py + 70, GREEN, 6)
    triangle(px + 370, py + 70, px + 344, py + 66, px + 366, py + 92, GREEN)


def pic_hormuz(px, py):
    # Sea with waves, tanker ship with containers.
    rect(px + 30, py + 140, px + 482, py + 195, (31, 97, 141))
    for wx in range(50, 480, 70):
        line(px + wx, py + 168, px + wx + 34, py + 160, WHITE, 3)
        line(px + wx + 34, py + 160, px + wx + 68, py + 168, WHITE, 3)
    # hull
    rect(px + 130, py + 108, px + 390, py + 148, (60, 60, 60))
    triangle(px + 390, py + 108, px + 390, py + 148, px + 420, py + 148, (60, 60, 60))
    # containers
    rect(px + 150, py + 78, px + 190, py + 108, RED)
    rect(px + 195, py + 78, px + 235, py + 108, YELLOW)
    rect(px + 240, py + 78, px + 280, py + 108, BLUE)
    rect(px + 285, py + 78, px + 325, py + 108, ORANGE)
    # bridge
    rect(px + 350, py + 82, px + 382, py + 108, WHITE)
    line(px + 366, py + 62, px + 366, py + 82, DARK, 4)


def pic_verstappen(px, py):
    # Checkered flag top right, red race car centre.
    fx, fy = px + 390, py + 24
    for r in range(4):
        for cc in range(6):
            col = BLACK if (r + cc) % 2 == 0 else WHITE
            rect(fx + cc * 14, fy + r * 14, fx + cc * 14 + 13, fy + r * 14 + 13, col)
    line(fx - 4, fy, fx - 4, fy + 70, DARK, 4)
    # car body
    rect(px + 120, py + 118, px + 392, py + 158, RED)
    triangle(px + 210, py + 118, px + 300, py + 118, px + 280, py + 88, RED)
    rect(px + 216, py + 92, px + 274, py + 118, (180, 220, 240))
    # wheels
    circle(px + 170, py + 162, 22, BLACK)
    circle(px + 170, py + 162, 10, LIGHTGREY)
    circle(px + 340, py + 162, 22, BLACK)
    circle(px + 340, py + 162, 10, LIGHTGREY)
    # ground line
    line(px + 60, py + 186, px + 452, py + 186, DARK, 3)


def pic_vanuatu(px, py):
    # Cracked ground, waves below, small shaking house.
    rect(px + 30, py + 150, px + 482, py + 195, SAND)
    # crack zigzag
    line(px + 120, py + 150, px + 170, py + 168, DARK, 4)
    line(px + 170, py + 168, px + 220, py + 152, DARK, 4)
    line(px + 220, py + 152, px + 280, py + 172, DARK, 4)
    line(px + 280, py + 172, px + 340, py + 154, DARK, 4)
    line(px + 340, py + 154, px + 400, py + 170, DARK, 4)
    # house with red roof and white walls, sitting on the cracked ground
    triangle(px + 200, py + 150, px + 260, py + 150, px + 230, py + 118, RED)
    rect(px + 215, py + 128, px + 245, py + 150, WHITE)
    rect(px + 226, py + 138, px + 234, py + 150, DARK)
    # waves
    for wx in range(50, 480, 70):
        line(px + wx, py + 128, px + wx + 34, py + 120, BLUE, 3)
        line(px + wx + 34, py + 120, px + wx + 68, py + 128, BLUE, 3)


PICS = [pic_cop31, pic_merkury, pic_nvidia, pic_hormuz, pic_verstappen, pic_vanuatu]


# ---------------------------------------------------------------- PNG encoder
def png_chunk(kind, data):
    c = struct.pack(">I", len(data)) + kind + data
    c += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return c


def encode_png():
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw.extend(fb[y * W * 3:(y + 1) * W * 3])
    idat = zlib.compress(bytes(raw), 9)
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IDAT", idat)
            + png_chunk(b"IEND", b""))


# ---------------------------------------------------------------- build
def build():
    rect(0, 0, W - 1, H - 1, WHITE)
    # Title banner
    rect(0, 0, W - 1, 87, NAVY)
    text_centered("24 NOVEMBER 2026", W // 2, 23, 6, WHITE)
    # Panels
    for i, (bg, l1, l2) in enumerate(PANELS):
        px = (i % 2) * 512
        py = 88 + (i // 2) * 312
        rect(px, py, px + 511, py + 311, bg)
        # border
        rect(px, py, px + 511, py + 2, DARK)
        rect(px, py + 309, px + 511, py + 311, DARK)
        rect(px, py, px + 2, py + 311, DARK)
        rect(px + 509, py, px + 511, py + 311, DARK)
        PICS[i](px, py)
        text_centered(l1, px + 256, py + 210, 3, BLACK)
        text_centered(l2, px + 256, py + 250, 3, BLACK)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "output")
    os.makedirs(out_dir, exist_ok=True)
    build()
    data = encode_png()
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("entry.png written")


if __name__ == "__main__":
    main()
