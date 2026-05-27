"""Shared FFmpeg utilities for video assembly pipeline."""

import asyncio
import struct
import subprocess
import zlib
from pathlib import Path


class FFmpegError(Exception):
    pass


def aspect_ratio_to_resolution(aspect_ratio: str) -> tuple[int, int]:
    ratio_map = {
        "9:16": (1080, 1920),
        "16:9": (1920, 1080),
        "4:3": (1440, 1080),
        "3:4": (1080, 1440),
        "1:1": (1080, 1080),
    }
    return ratio_map.get(aspect_ratio, (1024, 1536))


async def run_ffmpeg(args: list[str]) -> None:
    cmd = ["ffmpeg"] + args
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    await proc.wait()
    if proc.returncode != 0:
        raise FFmpegError(f"FFmpeg failed (code {proc.returncode}): {' '.join(cmd)}")


def create_blank_png() -> bytes:
    """Create a minimal 1x1 white PNG."""
    def _make_png(w, h, r, g, b):
        raw = b""
        for _ in range(h):
            raw += b"\x00" + bytes([r, g, b]) * w
        def chunk(ctype, data):
            c = ctype + data
            return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b"")
        )
    return _make_png(1, 1, 255, 255, 255)
