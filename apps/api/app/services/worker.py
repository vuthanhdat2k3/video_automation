"""ARQ worker task functions for pipeline generation."""
from uuid import UUID
from pathlib import Path

from app.database import async_session_factory
from app.models.shot import ShotModel
from app.models.asset import AssetModel
from app.models.job import JobModel
from app.services.asset_utils import save_generated_asset
from app.services.background_gen import BackgroundGenService
from app.services.keyframe_gen import KeyframeGenService
from app.services.tts import TTSService
from app.services.exporter import ExportService
from app.services.lipsync import LipSyncService, LipSyncError
from app.services.job import JobService
from app.services.websocket import manager
from app.config import settings
from app.services.storage import StorageManager
from app.logging import get_logger
from ai_2d_shared.enums import AssetType
from sqlalchemy import select

logger = get_logger("worker")


async def _complete_job(
    job_id: str | None,
    project_id: str,
    output_data: dict | None = None,
) -> None:
    if not job_id:
        return
    async with async_session_factory() as db:
        svc = JobService(db)
        result = await svc.complete(UUID(job_id), output_data or {})
        await manager.broadcast(UUID(project_id), {
            "type": "job.completed",
            "job": result.model_dump(),
        })
    logger.info("job completed", extra={"job_id": job_id})


async def _fail_job(job_id: str | None, project_id: str, error: str) -> None:
    if not job_id:
        return
    async with async_session_factory() as db:
        svc = JobService(db)
        result = await svc.fail(UUID(job_id), error)
        await manager.broadcast(UUID(project_id), {
            "type": "job.failed",
            "job": result.model_dump(),
        })
    logger.error("job failed", extra={"job_id": job_id, "error": error})


async def _update_progress(job_id: str | None, project_id: str, progress: float) -> None:
    """Update job progress and broadcast via WebSocket."""
    if not job_id:
        return
    async with async_session_factory() as db:
        svc = JobService(db)
        result = await svc.update_status(UUID(job_id), "in_progress", progress=progress)
        await manager.broadcast(UUID(project_id), {
            "type": "job.progress",
            "job": result.model_dump(),
        })


async def run_generate_background(ctx, project_id: str, shot_id: str, scene_id: str) -> bool:
    """Generate background image for a shot via job queue."""
    job_id = ctx.get("job_id")
    try:
        async with async_session_factory() as db:
            bg_svc = BackgroundGenService(db)
            png, prompt = await bg_svc.generate_for_scene(UUID(scene_id))

            asset = await save_generated_asset(
                db=db,
                project_id=UUID(project_id),
                asset_type=AssetType.BACKGROUND.value,
                filename=f"bg_shot_{shot_id}.png",
                data=png,
                metadata={"prompt": prompt, "shot_id": shot_id, "scene_id": scene_id},
            )

            result = await db.execute(select(ShotModel).where(ShotModel.id == UUID(shot_id)))
            shot = result.scalar_one_or_none()
            if shot:
                shot.background_asset_id = asset.id
            await db.commit()

        await _complete_job(job_id, project_id, {"asset_id": str(asset.id)})
        return True
    except Exception as e:
        await _fail_job(job_id, project_id, str(e))
        raise


async def run_lipsync_shot(ctx, project_id: str, shot_id: str) -> bool:
    """Generate lip-synced talking head for a shot via job queue."""
    job_id = ctx.get("job_id")
    try:
        async with async_session_factory() as db:
            result = await db.execute(select(ShotModel).where(ShotModel.id == UUID(shot_id)))
            shot = result.scalar_one_or_none()
            if not shot:
                raise ValueError(f"Shot {shot_id} not found")

            if not LipSyncService.needs_lipsync(shot):
                raise ValueError(f"Shot {shot_id} has no dialogue or missing assets")

            # Load keyframe image
            from app.models.asset import AssetModel
            from app.models.scene import SceneModel
            from app.config import settings
            from app.services.storage import StorageManager

            storage = StorageManager(settings.storage_root)

            kf_result = await db.execute(select(AssetModel).where(AssetModel.id == shot.keyframe_asset_id))
            kf_asset = kf_result.scalar_one_or_none()
            if not kf_asset:
                raise ValueError(f"Keyframe asset {shot.keyframe_asset_id} not found")

            audio_result = await db.execute(select(AssetModel).where(AssetModel.id == shot.audio_asset_id))
            audio_asset = audio_result.scalar_one_or_none()
            if not audio_asset:
                raise ValueError(f"Audio asset {shot.audio_asset_id} not found")

            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                input_img = tmp / "portrait.png"
                input_audio = tmp / "narration.mp3"
                output_video = tmp / "lipsync.mp4"

                img_path = storage.get_asset_path(UUID(project_id), kf_asset.path)
                aud_path = storage.get_asset_path(UUID(project_id), audio_asset.path)

                input_img.write_bytes(img_path.read_bytes())
                input_audio.write_bytes(aud_path.read_bytes())

                ls = LipSyncService()
                await ls.generate_talking_head(input_img, input_audio, output_video)

                video_bytes = output_video.read_bytes()
                asset = await save_generated_asset(
                    db=db,
                    project_id=UUID(project_id),
                    asset_type=AssetType.VIDEO_CLIP.value,
                    filename=f"lipsync_shot_{shot_id}.mp4",
                    data=video_bytes,
                    metadata={"shot_id": shot_id},
                )

                shot.video_export_id = asset.id
                await db.commit()

        await _complete_job(job_id, project_id, {"asset_id": str(asset.id)})
        return True
    except Exception as e:
        await _fail_job(job_id, project_id, str(e))
        raise


async def run_generate_keyframe(ctx, project_id: str, shot_id: str) -> bool:
    """Generate keyframe image for a shot via job queue."""
    job_id = ctx.get("job_id")
    try:
        async with async_session_factory() as db:
            kf_svc = KeyframeGenService(db)
            png, prompt = await kf_svc.generate_for_shot(UUID(shot_id))

            result = await db.execute(select(ShotModel).where(ShotModel.id == UUID(shot_id)))
            shot = result.scalar_one_or_none()
            if not shot:
                raise ValueError(f"Shot {shot_id} not found")

            asset = await save_generated_asset(
                db=db,
                project_id=UUID(project_id),
                asset_type=AssetType.KEYFRAME.value,
                filename=f"kf_shot_{shot_id}.png",
                data=png,
                metadata={"prompt": prompt, "shot_id": shot_id, "scene_id": str(shot.scene_id)},
            )

            shot.keyframe_asset_id = asset.id
            shot.generation_prompt = prompt
            shot.status = "keyframe_generated"
            await db.commit()

        await _complete_job(job_id, project_id, {"asset_id": str(asset.id), "prompt": prompt})
        return True
    except Exception as e:
        await _fail_job(job_id, project_id, str(e))
        raise


async def run_generate_audio(ctx, project_id: str, shot_id: str) -> bool:
    """Generate narration audio for a shot via job queue."""
    job_id = ctx.get("job_id")
    try:
        async with async_session_factory() as db:
            tts = TTSService(db=db)
            audio_bytes, text = await tts.generate_for_shot(UUID(shot_id))

            result = await db.execute(select(ShotModel).where(ShotModel.id == UUID(shot_id)))
            shot = result.scalar_one_or_none()
            if not shot:
                raise ValueError(f"Shot {shot_id} not found")

            voice = shot.audio.voice_profile or "vi-VN-NamMinhNeural"
            asset = await save_generated_asset(
                db=db,
                project_id=UUID(project_id),
                asset_type=AssetType.AUDIO.value,
                filename=f"audio_shot_{shot_id}.mp3",
                data=audio_bytes,
                metadata={"text": text, "shot_id": shot_id, "voice": voice},
            )

            shot.audio_asset_id = asset.id
            await db.commit()

        await _complete_job(job_id, project_id, {"asset_id": str(asset.id), "text": text})
        return True
    except Exception as e:
        await _fail_job(job_id, project_id, str(e))
        raise


async def run_export_scene(ctx, project_id: str, scene_id: str) -> bool:
    """Export scene as MP4 video via job queue."""
    job_id = ctx.get("job_id")
    try:
        async with async_session_factory() as db:
            export_svc = ExportService(db)
            mp4_bytes, filename = await export_svc.export_scene(UUID(scene_id))

            asset = await save_generated_asset(
                db=db,
                project_id=UUID(project_id),
                asset_type=AssetType.EXPORT.value,
                filename=filename,
                data=mp4_bytes,
                metadata={"scene_id": scene_id, "mime_type": "video/mp4"},
            )
            await db.commit()

        await _complete_job(job_id, project_id, {"asset_id": str(asset.id)})
        return True
    except Exception as e:
        await _fail_job(job_id, project_id, str(e))
        raise


async def run_concat_project(ctx, project_id: str) -> bool:
    """Concatenate all scene exports into final project MP4 (depends on batch parent)."""
    job_id = ctx.get("job_id")
    try:
        await _update_progress(job_id, project_id, 0.1)

        async with async_session_factory() as db:
            storage = StorageManager(settings.storage_root)
            job = await db.get(JobModel, UUID(job_id))

            # depends_on points to the parent batch job; children have batch_id == parent.id
            parent_id = job.depends_on
            child_result = await db.execute(
                select(JobModel).where(JobModel.batch_id == parent_id)
                .where(JobModel.status == "completed")
            )
            children = child_result.scalars().all()
            if not children:
                raise ValueError(f"No completed scene exports found for project {project_id}")

            await _update_progress(job_id, project_id, 0.3)

            export_paths = []
            for child in children:
                asset_id = child.output_json.get("asset_id") if child.output_json else None
                if asset_id:
                    asset = await db.get(AssetModel, UUID(asset_id))
                    if asset:
                        export_paths.append(storage.get_asset_path(UUID(project_id), asset.path))

            if not export_paths:
                raise ValueError("No export asset files found to concatenate")

            await _update_progress(job_id, project_id, 0.5)

            import asyncio, subprocess, tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                filelist = tmp / "filelist.txt"
                filelist.write_text(
                    "\n".join(f"file '{p}'" for p in export_paths) + "\n"
                )

                output = tmp / "project_final.mp4"
                proc = await asyncio.create_subprocess_exec(
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(filelist), "-c", "copy", str(output),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                await proc.wait()
                if proc.returncode != 0:
                    raise RuntimeError(f"FFmpeg concat failed (code {proc.returncode})")

                await _update_progress(job_id, project_id, 0.9)

                mp4_bytes = output.read_bytes()
                asset = await save_generated_asset(
                    db=db,
                    project_id=UUID(project_id),
                    asset_type=AssetType.EXPORT.value,
                    filename=f"project_{project_id}_final.mp4",
                    data=mp4_bytes,
                    metadata={"project_id": project_id, "scene_count": len(export_paths)},
                )
                await db.commit()

        await _complete_job(job_id, project_id, {"asset_id": str(asset.id)})
        return True
    except Exception as e:
        await _fail_job(job_id, project_id, str(e))
        raise
