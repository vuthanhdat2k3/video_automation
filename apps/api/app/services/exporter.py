import asyncio
import shutil
import tempfile
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
from app.services.ffmpeg_utils import (
    aspect_ratio_to_resolution,
    create_blank_png,
    run_ffmpeg,
    FFmpegError,
)


class ExportError(Exception):
    pass


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
        width, height = aspect_ratio_to_resolution(aspect_ratio)

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

        for idx, shot in enumerate(shots):
            dur = shot.duration_seconds or 4.0
            vf_parts = self._build_filter_chain(shot, scene, width, height)
            clip_path = work_dir / f"clip_{idx}.mp4"

            vid_path = await self._resolve_video_asset(shot, scene.project_id)
            if vid_path and vid_path.exists():
                await run_ffmpeg([
                    "-y", "-stream_loop", "-1", "-i", str(vid_path),
                    "-t", str(dur),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-vf", ",".join(vf_parts),
                    str(clip_path),
                ])
            else:
                frame_data = await self._resolve_frame_asset(shot, scene.project_id) or create_blank_png()
                (work_dir / f"frame_{idx}.png").write_bytes(frame_data)
                await run_ffmpeg([
                    "-y", "-loop", "1", "-i", str(work_dir / f"frame_{idx}.png"),
                    "-t", str(dur),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-vf", ",".join(vf_parts),
                    str(clip_path),
                ])

            clip_paths.append(clip_path)

            audio_asset_path = await self._resolve_audio_asset(shot, scene.project_id)
            if audio_asset_path:
                audio_paths.append(audio_asset_path)

            filelist_lines.append(f"file '{clip_path}'\n")

        # Generate subtitle file
        sub_path = None
        if project and getattr(project, "subtitle_enabled", False):
            font = getattr(project, "default_font", "Noto Sans SC")
            ass_content = SubtitleService.generate_subs(shots, width, height, fontname=font)
            if ass_content.strip():
                sub_path = work_dir / "subtitles.ass"
                sub_path.write_text(ass_content, encoding="utf-8")

        merged_video = work_dir / "merged_video.mp4"
        transition = getattr(scene, "transition_style", "fade")
        if transition and len(clip_paths) >= 2 and transition in TransitionService.XFADE_MAP:
            await self._build_xfade_video(clip_paths, shots, transition, merged_video)
        else:
            filelist_path = work_dir / "filelist.txt"
            filelist_path.write_text("".join(filelist_lines))
            await run_ffmpeg([
                "-y", "-f", "concat", "-safe", "0",
                "-i", str(filelist_path),
                "-c", "copy",
                str(merged_video),
            ])

        output_path = await self._merge_audio_and_subs(
            merged_video, audio_paths, scene, project, sub_path, work_dir,
        )

        mp4_bytes = output_path.read_bytes()
        return mp4_bytes, f"scene_{scene.id}.mp4"

    def _build_filter_chain(self, shot: ShotModel, scene: SceneModel, width: int, height: int) -> list[str]:
        """Build FFmpeg video filter chain for a shot."""
        vf_parts = [f"scale={width}:{height}"]

        cm = CameraMotionService.get_filter_string(shot, width, height)
        if cm:
            vf_parts.append(cm)

        grade = scene.grade_json or {}
        grade_filter = ColorGradeService.get_filter_string(
            lut_path=grade.get("lut_path"),
            colorbalance=grade.get("colorbalance"),
            eq_params=grade.get("eq"),
        )
        if grade_filter:
            vf_parts.append(grade_filter)

        if scene.shadow_enabled:
            shadow_svc = ShadowService()
            vf_parts.append(shadow_svc.get_shadow_filter(input_label="v", output_label="v_out"))

        vfx = scene.vfx_json or {}
        if vfx.get("rain", {}).get("enabled"):
            vf_parts.append(VFXOverlayService.get_rain_filter(width, height, vfx["rain"].get("opacity", 0.3)))
        if vfx.get("aura", {}).get("enabled"):
            vf_parts.append(VFXOverlayService.get_aura_filter(vfx["aura"].get("intensity", 0.5), vfx["aura"].get("color", "gold")))

        return vf_parts

    async def _resolve_video_asset(self, shot: ShotModel, project_id: UUID) -> Path | None:
        """Resolve path to existing video asset for a shot."""
        if not shot.video_export_id:
            return None
        vid_result = await self.db.execute(
            select(AssetModel).where(AssetModel.id == shot.video_export_id)
        )
        vid_asset = vid_result.scalar_one_or_none()
        if not vid_asset:
            return None
        path = self.storage.get_asset_path(project_id, vid_asset.path)
        return path if path.exists() else None

    async def _resolve_frame_asset(self, shot: ShotModel, project_id: UUID) -> bytes | None:
        """Resolve bytes of keyframe asset for a shot."""
        if not shot.keyframe_asset_id:
            return None
        asset_result = await self.db.execute(
            select(AssetModel).where(AssetModel.id == shot.keyframe_asset_id)
        )
        asset = asset_result.scalar_one_or_none()
        if not asset:
            return None
        frame_path = self.storage.get_asset_path(project_id, asset.path)
        return frame_path.read_bytes() if frame_path.exists() else None

    async def _resolve_audio_asset(self, shot: ShotModel, project_id: UUID) -> Path | None:
        """Resolve path to audio asset for a shot."""
        if not shot.audio_asset_id:
            return None
        asset_result = await self.db.execute(
            select(AssetModel).where(AssetModel.id == shot.audio_asset_id)
        )
        asset = asset_result.scalar_one_or_none()
        if not asset:
            return None
        audio_path = self.storage.get_asset_path(project_id, asset.path)
        return audio_path if audio_path.exists() else None

    async def _merge_audio_and_subs(
        self,
        video_path: Path,
        audio_paths: list[Path],
        scene: SceneModel,
        project: ProjectModel | None,
        sub_path: Path | None,
        work_dir: Path,
    ) -> Path:
        """Merge audio tracks and subtitles into the video."""
        output_path = work_dir / "output.mp4"

        if not audio_paths:
            return self._build_final_output(video_path, sub_path, output_path)

        # Merge audio tracks
        merged_audio = await self._merge_audio_tracks(audio_paths, scene, project, work_dir)
        if not merged_audio:
            return self._build_final_output(video_path, sub_path, output_path)

        # Combine video + audio + optional subtitles
        if sub_path:
            await run_ffmpeg([
                "-y", "-i", str(video_path),
                "-i", str(merged_audio),
                "-vf", SubtitleService.get_overlay_filter(sub_path),
                "-c:v", "libx264", "-c:a", "aac",
                "-shortest",
                str(output_path),
            ])
        else:
            await run_ffmpeg([
                "-y", "-i", str(video_path),
                "-i", str(merged_audio),
                "-c:v", "copy", "-c:a", "aac",
                "-shortest",
                str(output_path),
            ])
        return output_path

    async def _merge_audio_tracks(
        self,
        audio_paths: list[Path],
        scene: SceneModel,
        project: ProjectModel | None,
        work_dir: Path,
    ) -> Path | None:
        """Merge narration audio tracks, optionally with BGM."""
        merged_audio = work_dir / "merged_audio.mp3"
        audio_config = getattr(project, "audio_json", None) if project else None
        bgm = None
        volume = 1.0

        if audio_config:
            bgm_path_str = audio_config.get("background_music") if isinstance(audio_config, dict) else None
            volume = audio_config.get("volume", 1.0) if isinstance(audio_config, dict) else 1.0
            if bgm_path_str and isinstance(bgm_path_str, str) and len(bgm_path_str) == 36:
                bgm_asset_result = await self.db.execute(
                    select(AssetModel).where(AssetModel.id == UUID(bgm_path_str))
                )
                bgm_asset = bgm_asset_result.scalar_one_or_none()
                if bgm_asset:
                    bgm = self.storage.get_asset_path(scene.project_id, bgm_asset.path)

        if bgm or volume != 1.0:
            mixer = AudioMixer()
            mixed_bytes = await mixer.mix_for_scene(
                narration_paths=audio_paths,
                music_path=bgm,
                volume=volume,
                output_path=merged_audio,
            )
            if not mixed_bytes:
                return None
        else:
            audio_list_path = work_dir / "audio_list.txt"
            with open(audio_list_path, "w") as f:
                for ap in audio_paths:
                    f.write(f"file '{ap}'\n")
            await run_ffmpeg([
                "-y", "-f", "concat", "-safe", "0",
                "-i", str(audio_list_path),
                "-c", "copy",
                str(merged_audio),
            ])
        return merged_audio

    async def _build_final_output(self, video_path: Path, sub_path: Path | None, output_path: Path) -> Path:
        """Build final output with optional subtitles and no audio track."""
        if sub_path:
            await run_ffmpeg([
                "-y", "-i", str(video_path),
                "-vf", SubtitleService.get_overlay_filter(sub_path),
                "-c:v", "libx264",
                str(output_path),
            ])
        else:
            await run_ffmpeg([
                "-y", "-i", str(video_path),
                "-c:v", "copy",
                str(output_path),
            ])
        return output_path

    async def _build_xfade_video(
        self, clip_paths: list[Path], shots: list[ShotModel],
        transition_style: str, output_path: Path,
    ):
        """Assemble clips with xfade transitions via filter_complex."""
        n = len(clip_paths)
        durations = [s.duration_seconds or 4.0 for s in shots[:n]]

        td = 0.5
        filters = []
        prev_label = f"0:v"
        cum = durations[0]
        for i in range(1, n):
            xf = TransitionService.XFADE_MAP.get(transition_style, "fade")
            offset = max(cum - td, 0)
            out_label = f"x{i}"
            filters.append(f"[{prev_label}][{i}:v]xfade=transition={xf}:duration={td}:offset={offset}[{out_label}]")
            prev_label = out_label
            cum += durations[i]
        last_label = prev_label if n > 1 else "0:v"

        filter_complex = ";".join(filters) if filters else ""
        ffmpeg_args = ["-y"]
        for clip in clip_paths:
            ffmpeg_args += ["-i", str(clip)]

        if filter_complex:
            ffmpeg_args += ["-filter_complex", filter_complex]
            ffmpeg_args += ["-map", f"[{last_label}]"]
        else:
            ffmpeg_args += ["-map", "0:v"]
        ffmpeg_args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(output_path)]

        await run_ffmpeg(ffmpeg_args)
