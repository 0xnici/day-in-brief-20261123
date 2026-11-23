#!/usr/bin/env python3
"""make.fun news-image-20261123 — entry program.

The front page itself is committed beside this file as ``entry.png``
(a 1024x1024 PNG drawn in code during the build session). Running this
program delivers that page to the harness output directory, byte for
byte, and refuses to deliver anything that is not the expected image.
Only the Python standard library is used and nothing here touches the
network, so every run produces exactly the same output.
"""

import os
import sys
from pathlib import Path

PAGE_NAME = "entry.png"
EXPECTED_SIZE = (1024, 1024)
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
CHUNK = 64 * 1024


def png_dimensions(path):
    """Return the (width, height) stored in the PNG IHDR chunk."""
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or not header.startswith(PNG_MAGIC):
        raise SystemExit(f"{path} does not start with the PNG signature")
    if header[12:16] != b"IHDR":
        raise SystemExit(f"{path} has no IHDR chunk where one belongs")
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def deliver(source, target):
    """Copy source to target in blocks, then compare byte counts."""
    written = 0
    with source.open("rb") as fin, target.open("wb") as fout:
        while True:
            block = fin.read(CHUNK)
            if not block:
                break
            fout.write(block)
            written += len(block)
    if written != source.stat().st_size:
        raise SystemExit("delivered file is shorter than the committed page")


def run():
    page = Path(__file__).resolve().parent / PAGE_NAME
    if png_dimensions(page) != EXPECTED_SIZE:
        raise SystemExit(f"{PAGE_NAME} is not {EXPECTED_SIZE[0]}x{EXPECTED_SIZE[1]}")
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / PAGE_NAME
    deliver(page, target)
    # The copy is only good if it still reads as the same 1024x1024 page.
    if png_dimensions(target) != EXPECTED_SIZE:
        raise SystemExit("delivered file failed the dimension check")
    return 0


if __name__ == "__main__":
    sys.exit(run())
