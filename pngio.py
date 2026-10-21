#!/usr/bin/env python3
"""Minimal RGBA PNG reader/writer, no dependencies, used to crop screenshots."""
from __future__ import annotations

import struct
import zlib


def load_png(path: str) -> tuple[int, int, list[bytes]]:
    """Return (w, h, rows) where rows[y] holds the RGBA bytes of that row."""
    d = open(path, "rb").read()
    i, idat = 8, b""
    w = h = 0
    while i < len(d):
        ln = struct.unpack(">I", d[i:i + 4])[0]
        typ = d[i + 4:i + 8]
        if typ == b"IHDR":
            w, h, _bd, _ct = struct.unpack(">IIBB", d[i + 8:i + 18])
        elif typ == b"IDAT":
            idat += d[i + 8:i + 8 + ln]
        i += 12 + ln
    raw = zlib.decompress(idat)
    bpp, stride = 4, w * 4 + 1
    prev = bytearray(w * 4)
    rows: list[bytes] = []
    pos = 0
    for _ in range(h):
        f = raw[pos]
        line = bytearray(raw[pos + 1:pos + stride])
        pos += stride
        if f == 1:
            for x in range(bpp, len(line)):
                line[x] = (line[x] + line[x - bpp]) & 255
        elif f == 2:
            for x in range(len(line)):
                line[x] = (line[x] + prev[x]) & 255
        elif f == 3:
            for x in range(len(line)):
                a = line[x - bpp] if x >= bpp else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
        elif f == 4:
            for x in range(len(line)):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        rows.append(bytes(line))
        prev = line
    return w, h, rows


def save_png(path: str, w: int, h: int, rows: list[bytes]) -> None:
    def chunk(typ: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    raw = b"".join(b"\x00" + rows[y] for y in range(h))
    out = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    open(path, "wb").write(out)


def crop_rows(rows, w, h, x0, y0, x1, y1):
    """Crop the RGBA row list without writing a file."""
    x0, x1 = max(0, x0), min(w, x1)
    y0, y1 = max(0, y0), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"empty crop area: ({x0},{y0})-({x1},{y1}) of {w}x{h}")
    return x1 - x0, y1 - y0, [rows[y][x0 * 4:x1 * 4] for y in range(y0, y1)]


def crop(src: str, dst: str, x0: int, y0: int, x1: int, y1: int) -> tuple[int, int]:
    w, h, rows = load_png(src)
    cw, ch, cropped = crop_rows(rows, w, h, x0, y0, x1, y1)
    save_png(dst, cw, ch, cropped)
    return cw, ch


if __name__ == "__main__":
    import sys
    print(crop(sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])))
