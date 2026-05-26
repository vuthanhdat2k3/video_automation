"""Lip sync service using FFmpeg for talking head mock (MuseTalk integration)."""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from app.models.shot import ShotModel


class LipSyncError(Exception):
    pass


class LipSyncService:
    """Generate talking head video from character portrait + TTS audio.

    Uses MuseTalk when available (CUDA), falls back to FFmpeg-based
    mock that creates a timed video with the portrait image + audio.
    """

    def __init__(self, model_path: str | None = None, device: str = "cpu"):
        self.model_path = model_path
        self.device = device

    async def generate_talking_head(
        self,
        image_path: Path,
        audio_path: Path,
        output_path: Path,
        fps: int = 25,
    ) -> Path:
        """Generate talking head video from portrait + audio.

        In production, this calls MuseTalk inference.
        The FFmpeg fallback creates a slideshow video with audio
        that matches the expected output format.
        """
        try:
            # Try real MuseTalk inference
            return await self._run_musetalk(image_path, audio_path, output_path, fps)
        except (ImportError, FileNotFoundError, LipSyncError):
            # Fallback: FFmpeg portrait + audio into MP4
            return await self._run_fallback(image_path, audio_path, output_path, fps)

    async def _run_musetalk(
        self, image_path: Path, audio_path: Path, output_path: Path, fps: int
    ) -> Path:
        """Run MuseTalk inference via subprocess."""
        import sys
        musetalk_dir = Path(self.model_path) if self.model_path else Path.home() / "pipeline" / "MuseTalk"
        if not musetalk_dir.exists():
            raise FileNotFoundError(f"MuseTalk not found at {musetalk_dir}")

        cmd = [
            sys.executable, "-m", "musetalk",
            "--video", str(image_path),
            "--audio", str(audio_path),
            "--output", str(output_path),
            "--fps", str(fps),
        ]
        if self.device == "cuda":
            cmd.append("--device")
            cmd.append("cuda")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise LipSyncError(f"MuseTalk failed: {stderr.decode()[:500]}")
        return output_path

    async def _run_fallback(
        self, image_path: Path, audio_path: Path, output_path: Path, fps: int
    ) -> Path:
        """FFmpeg fallback: create video from portrait + audio."""
        # Get audio duration
        dur_cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *dur_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        duration = float(stdout.decode().strip()) if stdout else 4.0

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(image_path),
            "-i", str(audio_path),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            "-t", str(duration),
            "-vf", f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
            str(output_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode != 0:
            raise LipSyncError("FFmpeg fallback failed")
        return output_path

    @staticmethod
    def needs_lipsync(shot: ShotModel) -> bool:
        """Check if shot has dialogue that benefits from lip sync."""
        return bool(shot.description and shot.keyframe_asset_id and shot.audio_asset_id)
