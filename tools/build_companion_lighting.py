#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate the original studio light probe (no downloaded textures)."""
import math
from pathlib import Path


def build(path):
    width, height = 512, 256
    data = bytearray(b'#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 256 +X 512\n')
    # Neutral softboxes preserve the user's theme hues on reflective surfaces.
    lights = [(.30, .31, .10, .12, (4.8, 4.8, 4.8)),
              (.74, .42, .045, .25, (3.3, 3.3, 3.3)),
              (.52, .14, .20, .035, (3.2, 3.2, 3.2)),
              (.04, .43, .035, .18, (2.2, 2.2, 2.2))]
    for y in range(height):
        row = []
        for x in range(width):
            u, v = x / width, y / height
            rgb = [.12 + .08 * (1-v)] * 3
            for cx, cy, sx, sy, color in lights:
                dx = min(abs(u-cx), 1-abs(u-cx)) / sx
                dy = abs(v-cy) / sy
                strength = math.exp(-(dx**6 + dy**6) * 2)
                rgb = [a+b*strength for a,b in zip(rgb,color)]
            mantissa, exponent = math.frexp(max(rgb))
            factor = mantissa * 256 / max(rgb)
            row.append([min(255,int(c*factor)) for c in rgb]+[exponent+128])
        data.extend((2,2,width >> 8,width & 255))
        for channel in range(4):
            for start in range(0,width,127):
                pixels=row[start:start+127]
                data.append(len(pixels)); data.extend(pixel[channel] for pixel in pixels)
    path.write_bytes(data)


if __name__ == '__main__':
    build(Path(__file__).resolve().parents[1]/'assets/companion/studio.hdr')
