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
from app.services.storage import StorageManager
from app.services.camera import CameraMotionService
from app.services.subtitle import SubtitleService
from app.services.transition import TransitionService
from app.services.audio_mixer import AudioMixer
from app.services.color_grade import ColorGradeService
from app.services.shadow import ShadowService
from app.services.vfx_overlay import VFXOverlayService


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
    """Assemble keyframes + audio into video via FFmpeg with camera motion and subtitles."""

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
            return await self._assemble_video(work_dir, scene, project, shots, width, height)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    async def _assemble_video(self, work_dir: Path, scene: SceneModel,
                               project: ProjectModel | None,
                               shots: list[ShotModel], width: int, height: int) -> tuple[bytes, str]:
        clip_paths = []
        audio_paths = []
        filelist_lines = []
        temp_idx = 0

        for shot in shots:
            dur = shot.duration_seconds or 4.0

            # Build per-shot video filter chain
            vf_parts = []
            vf_parts.append(f"scale={width}:{height}")

            cm = CameraMotionService.get_filter_string(shot, width, height)
            if cm:
                vf_parts.append(cm)

            # Color grade from scene config
            grade = scene.grade_json or {}
            grade_filter = ColorGradeService.get_filter_string(
                lut_path=grade.get("lut_path"),
                colorbalance=grade.get("colorbalance"),
                eq_params=grade.get("eq"),
            )
            if grade_filter:
                vf_parts.append(grade_filter)

            # Shadow from scene config
            if scene.shadow_enabled:
                shadow_svc = ShadowService()
                shadow_filter = shadow_svc.get_shadow_filter(
                    input_label="v", output_label="v_out",
                )
                vf_parts.append(shadow_filter)

            # VFX from scene config
            vfx = scene.vfx_json or {}
            if vfx.get("rain", {}).get("enabled"):
                rain_filter = VFXOverlayService.get_rain_filter(
                    width, height, vfx["rain"].get("opacity", 0.3),
                )
                vf_parts.append(rain_filter)
            if vfx.get("aura", {}).get("enabled"):
                aura_filter = VFXOverlayService.get_aura_filter(
                    vfx["aura"].get("intensity", 0.5),
                    vfx["aura"].get("color", "gold"),
                )
                vf_parts.append(aura_filter)

            # Check if lip-sync video exists
            if shot.video_export_id:
                vid_result = await self.db.execute(
                    select(AssetModel).where(AssetModel.id == shot.video_export_id)
                )
                vid_asset = vid_result.scalar_one_or_none()
                if vid_asset:
                    vid_path = self.storage.get_asset_path(scene.project_id, vid_asset.path)
                    if vid_path.exists():
                        clip_path = work_dir / f"clip_{temp_idx}.mp4"
                        await self._run_ffmpeg([
                            "-y", "-i", str(vid_path),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-vf", ",".join(vf_parts),
                            str(clip_path),
                        ])
                        clip_paths.append(clip_path)

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
                        continue

            # Fallback: generate still frame clip with camera motion + post-prod filters
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
                frame_data = self._create_blank_frame(dur)

            frame_path = work_dir / f"frame_{temp_idx}.png"
            frame_path.write_bytes(frame_data)

            clip_path = work_dir / f"clip_{temp_idx}.mp4"
            await self._run_ffmpeg([
                "-y", "-loop", "1", "-i", str(frame_path),
                "-t", str(dur),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-vf", ",".join(vf_parts),
                str(clip_path),
            ])
            clip_paths.append(clip_path)

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

        # Generate subtitle file
        sub_path = None
        if project and getattr(project, "subtitle_enabled", False):
            font = getattr(project, "default_font", "Noto Sans SC") if project else "Noto Sans SC"
            ass_content = SubtitleService.generate_subs(shots, width, height, fontname=font)
            if ass_content.strip():
                sub_path = work_dir / "subtitles.ass"
                sub_path.write_text(ass_content, encoding="utf-8")

        merged_video = work_dir / "merged_video.mp4"

        # Use TransitionService xfade when 2+ clips with transition configured
        transition = getattr(scene, "transition_style", "fade")
        if transition and len(clip_paths) >= 2 and transition in TransitionService.XFADE_MAP:
            await self._build_xfade_video(clip_paths, shots, transition, merged_video)
        else:
            filelist_path = work_dir / "filelist.txt"
            filelist_path.write_text("".join(filelist_lines))
            await self._run_ffmpeg([
                "-y", "-f", "concat", "-safe", "0",
                "-i", str(filelist_path),
                "-c", "copy",
                str(merged_video),
            ])

        output_path = work_dir / "output.mp4"

        # Use AudioMixer when BGM or volume config present
        if audio_paths:
            audio_config = getattr(project, "audio_json", None) if project else None
            bgm = None
            volume = 1.0
            if audio_config:
                bgm_path = audio_config.get("background_music") or getattr(audio_config, "background_music", None)
                volume = audio_config.get("volume", 1.0) if isinstance(audio_config, dict) else 1.0

            merged_audio = work_dir / "merged_audio.mp3"

            if bgm or volume != 1.0:
                mixer = AudioMixer()
                if bgm:
                    bgm_asset_result = await self.db.execute(
                        select(AssetModel).where(AssetModel.id == UUID(bgm))
                    ) if isinstance(bgm, str) and len(bgm) == 36 else (None,)
                    bgm_asset = bgm_asset_result.scalar_one_or_none() if bgm_asset_result else None
                    if bgm_asset:
                        bgm = self.storage.get_asset_path(scene.project_id, bgm_asset.path)

                mixed_bytes = await mixer.mix_for_scene(
                    narration_paths=audio_paths,
                    music_path=bgm,
                    volume=volume,
                    output_path=merged_audio,
                )
                if not mixed_bytes:
                    audio_paths = []
            else:
                audio_list_path = work_dir / "audio_list.txt"
                with open(audio_list_path, "w") as f:
                    for ap in audio_paths:
                        f.write(f"file '{ap}'\n")
                await self._run_ffmpeg([
                    "-y", "-f", "concat", "-safe", "0",
                    "-i", str(audio_list_path),
                    "-c", "copy",
                    str(merged_audio),
                ])

        if audio_paths:
            if sub_path:
                await self._run_ffmpeg([
                    "-y", "-i", str(merged_video),
                    "-i", str(merged_audio),
                    "-vf", SubtitleService.get_overlay_filter(sub_path),
                    "-c:v", "libx264", "-c:a", "aac",
                    "-shortest",
                    str(output_path),
                ])
            else:
                await self._run_ffmpeg([
                    "-y", "-i", str(merged_video),
                    "-i", str(merged_audio),
                    "-c:v", "copy", "-c:a", "aac",
                    "-shortest",
                    str(output_path),
                ])
        else:
            if sub_path:
                await self._run_ffmpeg([
                    "-y", "-i", str(merged_video),
                    "-vf", SubtitleService.get_overlay_filter(sub_path),
                    "-c:v", "libx264",
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

    async def _build_xfade_video(
        self, clip_paths: list[Path], shots: list[ShotModel],
        transition_style: str, output_path: Path,
    ):
        """Assemble clips with xfade transitions via filter_complex."""
        segment_labels = []
        segment_durations = []
        transition_styles = []

        for i, (clip, shot) in enumerate(zip(clip_paths, shots[:len(clip_paths)])):
            label = f"s{i}"
            segment_labels.append(label)
            segment_durations.append(shot.duration_seconds or 4.0)
            transition_styles.append(transition_style)

        # Build xfade chain filter string
        xfade_filter, last_label = TransitionService.build_xfade_chain(
            segment_labels, transition_styles, segment_durations, 0.5,
        )

        # Build input arguments: -i clip0 -i clip1 ...
        ffmpeg_args = ["-y"]
        for clip in clip_paths:
            ffmpeg_args += ["-i", str(clip)]

        # Map inputs to labels: [0:v][1:v]...
        input_labels = [f"[{i}:v]" for i in range(len(clip_paths))]
        filter_complex = "".join(input_labels) + ";\n" + xfade_filter

        ffmpeg_args += ["-filter_complex", filter_complex]
        ffmpeg_args += ["-map", f"[{last_label}]", "-c:v", "libx264", "-pix_fmt", "yuv420p"]
        ffmpeg_args += [str(output_path)]

        await self._run_ffmpeg(ffmpeg_args)

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
