import asyncio
import shutil
import subprocess
import time
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import NotFoundException
from app.models.asset import AssetModel
from app.models.project import ProjectModel
from app.models.scene import SceneModel
from app.models.shot import ShotModel
from app.services.asset_utils import save_generated_asset
from app.services.storage import StorageManager
from ai_2d_shared.enums import AssetType


class ExportError(Exception):
    pass


def _aspect_ratio_to_resolution(aspect_ratio: str) -> tuple[int, int]:
    ratio_map = {
        "9:16": (1080, 1920),
        "16:9": (1920, 1080),
        "4:3": (1440, 1080),
        "3:4": (1080, 1440),
        "1:1": (1080, 1080),
    }
    return ratio_map.get(aspect_ratio, (1024, 1536))


class ExportService:
    """Assemble keyframes + audio into video via FFmpeg."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = StorageManager(settings.storage_root)

    async def export_scene(self, scene_id: UUID) -> tuple[bytes, str]:
        """Export scene as MP4. Returns (mp4_bytes, filename)."""
        scene_result = await self.db.execute(
            select(SceneModel).where(SceneModel.id == scene_id)
        )
        scene = scene_result.scalar_one_or_none()
        if not scene:
            raise NotFoundException(f"Scene {scene_id} not found")

        project_result = await self.db.execute(
            select(ProjectModel).where(ProjectModel.id == scene.project_id)
        )
        project = project_result.scalar_one_or_none()
        aspect_ratio = project.aspect_ratio if project else "9:16"
        width, height = _aspect_ratio_to_resolution(aspect_ratio)

        shot_result = await self.db.execute(
            select(ShotModel)
            .where(ShotModel.scene_id == scene_id)
            .order_by(ShotModel.order_index)
        )
        shots = shot_result.scalars().all()
        if not shots:
            raise NotFoundException(f"No shots found for scene {scene_id}")

        work_dir = Path(f"/tmp/export_{scene_id}_{int(time.time())}")
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            return await self._assemble_video(work_dir, scene, shots, width, height)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    async def _assemble_video(self, work_dir: Path, scene: SceneModel,
                               shots: list[ShotModel], width: int, height: int) -> tuple[bytes, str]:
        clip_paths = []
        audio_paths = []
        filelist_lines = []
        temp_idx = 0

        for shot in shots:
            dur = shot.duration_seconds or 4.0

            # Get keyframe image
            frame_data = None
            if shot.keyframe_asset_id:
                asset_result = await self.db.execute(
                    select(AssetModel).where(AssetModel.id == shot.keyframe_asset_id)
                )
                asset = asset_result.scalar_one_or_none()
                if asset:
                    frame_path = self.storage.get_asset_path(scene.project_id, asset.path)
                    if frame_path.exists():
                        frame_data = frame_path.read_bytes()

            if not frame_data:
                # Create a blank placeholder frame (white)
                frame_data = self._create_blank_frame(dur)

            frame_path = work_dir / f"frame_{temp_idx}.png"
            frame_path.write_bytes(frame_data)

            # Create video clip from frame
            clip_path = work_dir / f"clip_{temp_idx}.mp4"
            await self._run_ffmpeg([
                "-y", "-loop", "1", "-i", str(frame_path),
                "-t", str(dur),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-vf", f"scale={width}:{height}",
                str(clip_path),
            ])
            clip_paths.append(clip_path)

            # Get audio
            if shot.audio_asset_id:
                asset_result = await self.db.execute(
                    select(AssetModel).where(AssetModel.id == shot.audio_asset_id)
                )
                asset = asset_result.scalar_one_or_none()
                if asset:
                    audio_path = self.storage.get_asset_path(scene.project_id, asset.path)
                    if audio_path.exists():
                        audio_paths.append(audio_path)

            filelist_lines.append(f"file '{clip_path}'\n")
            temp_idx += 1

        # Concat all video clips
        filelist_path = work_dir / "filelist.txt"
        filelist_path.writelines(filelist_lines)

        merged_video = work_dir / "merged_video.mp4"
        await self._run_ffmpeg([
            "-y", "-f", "concat", "-safe", "0",
            "-i", str(filelist_path),
            "-c", "copy",
            str(merged_video),
        ])

        # Add audio if available
        output_path = work_dir / "output.mp4"
        if audio_paths:
            audio_list_path = work_dir / "audio_list.txt"
            with open(audio_list_path, "w") as f:
                for ap in audio_paths:
                    f.write(f"file '{ap}'\n")
            merged_audio = work_dir / "merged_audio.mp3"
            await self._run_ffmpeg([
                "-y", "-f", "concat", "-safe", "0",
                "-i", str(audio_list_path),
                "-c", "copy",
                str(merged_audio),
            ])
            await self._run_ffmpeg([
                "-y", "-i", str(merged_video),
                "-i", str(merged_audio),
                "-c:v", "copy", "-c:a", "aac",
                "-shortest",
                str(output_path),
            ])
        else:
            await self._run_ffmpeg([
                "-y", "-i", str(merged_video),
                "-c:v", "copy",
                str(output_path),
            ])

        mp4_bytes = output_path.read_bytes()
        filename = f"scene_{scene.id}.mp4"
        return mp4_bytes, filename

    async def _run_ffmpeg(self, args: list[str]) -> None:
        cmd = ["ffmpeg"] + args
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode != 0:
            raise ExportError(f"FFmpeg failed (code {proc.returncode}): {' '.join(cmd)}")

    def _create_blank_frame(self, duration: float) -> bytes:
        """Create a 1024x1536 white PNG as placeholder (1x1 px minimal PNG)."""
        import struct, zlib

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
