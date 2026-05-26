"""ARQ worker task functions for pipeline generation."""
from uuid import UUID

from app.config import settings
from app.database import async_session_factory
from app.models.shot import ShotModel
from app.models.scene import SceneModel
from app.models.project import ProjectModel
from app.services.asset_utils import save_generated_asset
from app.services.background_gen import BackgroundGenService
from app.services.keyframe_gen import KeyframeGenService
from app.services.tts import TTSService
from app.services.exporter import ExportService
from app.services.job import JobService
from ai_2d_shared.enums import AssetType
from sqlalchemy import select


async def _get_project_id_from_shot(db, shot_id: UUID) -> UUID:
    result = await db.execute(
        select(SceneModel).join(ShotModel, ShotModel.scene_id == SceneModel.id)
        .where(ShotModel.id == shot_id)
    )
    scene = result.scalar_one_or_none()
    return scene.project_id if scene else None


async def run_generate_background(ctx, project_id: str, shot_id: str, scene_id: str) -> bool:
    """Generate background image for a shot via job queue."""
    async with async_session_factory() as db:
        job_svc = JobService(db)
        try:
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
            return True
        except Exception as e:
            await db.rollback()
            raise


async def run_generate_keyframe(ctx, project_id: str, shot_id: str) -> bool:
    """Generate keyframe image for a shot via job queue."""
    async with async_session_factory() as db:
        try:
            kf_svc = KeyframeGenService(db)
            png, prompt = await kf_svc.generate_for_shot(UUID(shot_id))

            result = await db.execute(select(ShotModel).where(ShotModel.id == UUID(shot_id)))
            shot = result.scalar_one_or_none()
            if not shot:
                raise ValueError(f"Shot {shot_id} not found")

            scene_result = await db.execute(select(SceneModel).where(SceneModel.id == shot.scene_id))
            scene = scene_result.scalar_one_or_none()

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
            return True
        except Exception as e:
            await db.rollback()
            raise


async def run_generate_audio(ctx, project_id: str, shot_id: str) -> bool:
    """Generate narration audio for a shot via job queue."""
    async with async_session_factory() as db:
        try:
            tts = TTSService(db=db)
            audio_bytes, text = await tts.generate_for_shot(UUID(shot_id))

            result = await db.execute(select(ShotModel).where(ShotModel.id == UUID(shot_id)))
            shot = result.scalar_one_or_none()
            if not shot:
                raise ValueError(f"Shot {shot_id} not found")

            scene_result = await db.execute(select(SceneModel).where(SceneModel.id == shot.scene_id))
            scene = scene_result.scalar_one_or_none()

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
            return True
        except Exception as e:
            await db.rollback()
            raise


async def run_export_scene(ctx, project_id: str, scene_id: str) -> bool:
    """Export scene as MP4 video via job queue."""
    async with async_session_factory() as db:
        try:
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
            return True
        except Exception as e:
            await db.rollback()
            raise
