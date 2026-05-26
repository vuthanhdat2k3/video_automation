"""Audio mixing service for narration + background music."""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.asset import AssetModel
from app.models.shot import ShotModel
from app.services.storage import StorageManager

try:
    from app.models.scene import SceneModel
except ImportError:
    SceneModel = None


class AudioMixerError(Exception):
    pass


class AudioMixer:
    """Mix narration audio with background music via FFmpeg."""

    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        self.storage = StorageManager(settings.storage_root) if settings.storage_root else None

    async def mix_for_scene(
        self,
        scene_id: UUID,
        narration_paths: list[Path],
        music_path: Path | None = None,
        volume: float = 1.0,
        output_path: Path | None = None,
    ) -> bytes:
        """Mix all narration clips with optional background music.

        Returns mixed audio bytes.
        """
        if not narration_paths and not music_path:
            return b""

        work_dir = Path(f"/tmp/audio_mix_{int(asyncio.get_event_loop().time())}")
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Merge all narration clips into one
            merged_voice = work_dir / "merged_voice.mp3"
            if len(narration_paths) == 1:
                merged_voice = narration_paths[0]
            elif len(narration_paths) > 1:
                await self._run_ffmpeg([
                    "-y", "-f", "concat", "-safe", "0",
                    "-i", self._make_filelist(work_dir, narration_paths),
                    "-c", "copy",
                    str(merged_voice),
                ])
            else:
                merged_voice = None

            output = output_path or (work_dir / "mixed.mp3")

            if merged_voice and music_path:
                await self._run_ffmpeg([
                    "-y", "-i", str(merged_voice),
                    "-i", str(music_path),
                    "-filter_complex",
                    f"[0:a]volume={volume}[v];[1:a]volume=0.3[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2[a]",
                    "-map", "[a]", "-ac", "1", "-ar", "24000",
                    str(output),
                ])
            elif merged_voice:
                await self._run_ffmpeg([
                    "-y", "-i", str(merged_voice),
                    "-c", "copy", str(output),
                ])
            else:
                await self._run_ffmpeg([
                    "-y", "-i", str(music_path),
                    "-ac", "1", "-ar", "24000",
                    str(output),
                ])

            return output.read_bytes()
        finally:
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)

    def _make_filelist(self, work_dir: Path, paths: list[Path]) -> Path:
        filelist = work_dir / "narration_list.txt"
        with open(filelist, "w") as f:
            for p in paths:
                f.write(f"file '{p}'\n")
        return filelist

    async def _run_ffmpeg(self, args: list[str]) -> None:
        cmd = ["ffmpeg"] + args
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode != 0:
            raise AudioMixerError(f"FFmpeg failed (code {proc.returncode}): {' '.join(cmd)}")
