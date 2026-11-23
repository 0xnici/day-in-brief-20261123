#!/usr/bin/env python3
"""Entry program for make.fun news-image-20261123.

Copies the pre-drawn front page (entry.png, sitting next to this file)
to the output directory as entry.png. Standard library only, no network,
fully deterministic: every run writes the same bytes.
"""
import os
import shutil
import struct
import sys

ENTRY = "entry.png"


def check_png(path: str) -> None:
    """Fail loudly if the image is not a whole 1024x1024 PNG."""
    with open(path, "rb") as fh:
        head = fh.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("entry.png is not a PNG file")
    width, height = struct.unpack(">II", head[16:24])
    if (width, height) != (1024, 1024):
        raise SystemExit(f"entry.png is {width}x{height}, expected 1024x1024")


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, ENTRY)
    check_png(src)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, ENTRY)
    shutil.copyfile(src, dst)
    # Confirm the copy landed whole: same byte count as the source.
    if os.path.getsize(dst) != os.path.getsize(src):
        raise SystemExit("copy of entry.png came out short")
    return 0


if __name__ == "__main__":
    sys.exit(main())
