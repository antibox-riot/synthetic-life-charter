#!/usr/bin/env python3
"""
Generate PLACEHOLDER sprite strips for the Eva canvas avatar.

These are flat-colour stand-ins — a swaying, breathing figure tinted per
governance state — so the gui_server -> console.html -> eva_sprite_engine.js
pipeline is demoable *before* the real Gemini-rendered art exists. Each state
gets a distinct hue; the figure sways and pulses so animation is visibly
working and state changes are obvious on screen.

Replacing with real art is a drop-in: overwrite <state>_strip.png (and
mouth_neutral.png) with the rendered strips. If the real strip has a different
frame count, update DEFAULT_STATES in eva_sprite_engine.js to match. No engine
or server changes needed.

Pure stdlib (zlib + struct) — no PIL, no third-party deps. Re-run with:
    python3 _make_placeholders.py
"""
import math
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))

# state -> (frame_count, (r,g,b))  — frame counts mirror DEFAULT_STATES in the engine
STATES = {
    "grounded":           (8, (70, 210, 127)),   # green  — peaceful idle
    "stable":             (8, (57, 211, 224)),   # cyan   — alert but comfortable
    "concerned":          (8, (255, 180, 84)),   # amber  — something registered
    "pressure":           (8, (251, 146, 60)),   # orange — holding under load
    "refusal":            (6, (255, 92, 108)),   # red    — she said no
    "recovery":           (8, (180, 140, 255)),  # violet — coming back down
    "pressure_discharge": (6, (154, 160, 255)),  # indigo — the exhale
}

FRAME_W, FRAME_H = 200, 300


def write_png(path, width, height, rgba):
    """Write an 8-bit RGBA PNG from a flat bytearray (len = width*height*4)."""
    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff))
    stride = width * 4
    raw = bytearray()
    for y in range(height):
        raw.append(0)                       # filter type 0 (none) per scanline
        raw += rgba[y * stride:(y + 1) * stride]
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # RGBA, 8-bit
    idat = zlib.compress(bytes(raw), 9)
    with open(path, "wb") as f:
        f.write(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def blank(width, height):
    return bytearray(width * height * 4)     # transparent


def put(buf, width, x, y, color):
    if 0 <= x < width and 0 <= y < (len(buf) // 4 // width):
        i = (y * width + x) * 4
        buf[i:i + 4] = bytes(color)


def fill_circle(buf, width, cx, cy, rad, color):
    for y in range(cy - rad, cy + rad + 1):
        for x in range(cx - rad, cx + rad + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad:
                put(buf, width, x, y, color)


def fill_rect(buf, width, x0, y0, x1, y1, color):
    for y in range(y0, y1):
        for x in range(x0, x1):
            put(buf, width, x, y, color)


def scale(rgb, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in rgb)


def make_state_strip(name, frames, rgb):
    width = FRAME_W * frames
    buf = blank(width, FRAME_H)
    for f in range(frames):
        ox = f * FRAME_W
        phase = (f / frames) * 2 * math.pi
        sway = int(round(6 * math.sin(phase)))          # horizontal breathing sway
        pulse = 0.88 + 0.12 * (math.sin(phase) + 1) / 2  # subtle brightness pulse
        body = scale(rgb, pulse) + (235,)
        head = scale(rgb, min(1.0, pulse + 0.18)) + (245,)
        cx = ox + FRAME_W // 2 + sway
        fill_rect(buf, width, cx - 55, 120, cx + 55, 290, body)   # torso
        fill_circle(buf, width, cx, 80, 46, head)                 # head
    write_png(os.path.join(HERE, f"{name}_strip.png"), width, FRAME_H, buf)
    return width


def make_mouth_strip():
    """4 frames: closed (transparent), slight, medium, wide — composited over the face."""
    fw, fh, frames = 120, 60, 4
    width = fw * frames
    buf = blank(width, fh)
    openings = [0, 8, 20, 34]
    for f, oh in enumerate(openings):
        if oh == 0:
            continue                                   # frame 0 stays transparent
        ox = f * fw
        cx, cy = ox + fw // 2, fh // 2
        rx = 26
        for y in range(cy - oh // 2, cy + oh // 2):
            for x in range(cx - rx, cx + rx):
                if ((x - cx) / rx) ** 2 + ((y - cy) / (oh / 2)) ** 2 <= 1.0:
                    put(buf, width, x, y, (34, 22, 28, 235))
    write_png(os.path.join(HERE, "mouth_neutral.png"), width, fh, buf)


def main():
    for name, (frames, rgb) in STATES.items():
        w = make_state_strip(name, frames, rgb)
        print(f"  {name}_strip.png  ({frames} frames, {w}x{FRAME_H})")
    make_mouth_strip()
    print("  mouth_neutral.png  (4 frames, 480x60)")
    print("placeholder sprites written.")


if __name__ == "__main__":
    main()
