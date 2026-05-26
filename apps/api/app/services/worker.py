"""ARQ worker task functions for pipeline generation."""
from uuid import UUID

from app.database import async_session_factory
from app.models.shot import ShotModel
from app.services.asset_utils import save_generated_asset
from app.services.background_gen import BackgroundGenService
from app.services.keyframe_gen import KeyframeGenService
from app.services.tts import TTSService
from app.services.exporter import ExportService
from app.services.job import JobService
from ai_2d_shared.enums import AssetType
from sqlalchemy import select


async def _complete_job(job_id: str | None, output_data: dict | None = None) -> None:
    if not job_id:
        return
    async with async_session_factory() as db:
        svc = JobService(db)
        await svc.complete(UUID(job_id), output_data or {})


async def _fail_job(job_id: str | None, error: str) -> None:
    if not job_id:
        return
    async with async_session_factory() as db:
        svc = JobService(db)
        await svc.fail(UUID(job_id), error)


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

        await _complete_job(job_id, {"asset_id": str(asset.id)})
        return True
    except Exception as e:
        await _fail_job(job_id, str(e))
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

        await _complete_job(job_id, {"asset_id": str(asset.id), "prompt": prompt})
        return True
    except Exception as e:
        await _fail_job(job_id, str(e))
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

        await _complete_job(job_id, {"asset_id": str(asset.id), "text": text})
        return True
    except Exception as e:
        await _fail_job(job_id, str(e))
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

        await _complete_job(job_id, {"asset_id": str(asset.id)})
        return True
    except Exception as e:
        await _fail_job(job_id, str(e))
        raise
