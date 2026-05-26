from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.shot import ShotCreate, ShotUpdate
from ai_2d_shared.enums import AssetType

from app.database import get_db
from app.exceptions import NotFoundException
from app.models.scene import SceneModel
from app.models.shot import ShotModel
from app.models.asset import AssetModel
from app.services.asset_utils import save_generated_asset
from app.services.shot import ShotService
from app.services.background_gen import BackgroundGenService
from app.services.keyframe_gen import KeyframeGenService
from app.services.tts import TTSService
from app.services.exporter import ExportService

router = APIRouter()


def get_shot_service(db: AsyncSession = Depends(get_db)) -> ShotService:
    return ShotService(db=db)


@router.get("/scenes/{scene_id}/shots", response_model=dict)
async def list_shots(
    scene_id: UUID,
    service: ShotService = Depends(get_shot_service),
):
    shots = await service.list_by_scene(scene_id)
    return {"data": [s.model_dump() for s in shots], "error": None}


@router.post("/scenes/{scene_id}/shots", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_shot(
    scene_id: UUID,
    data: ShotCreate,
    db: AsyncSession = Depends(get_db),
    service: ShotService = Depends(get_shot_service),
):
    result = await db.execute(select(SceneModel).where(SceneModel.id == scene_id))
    if not result.scalar_one_or_none():
        raise NotFoundException(f"Scene {scene_id} not found")

    if data.scene_id != scene_id:
        data.scene_id = scene_id

    shot = await service.create(scene_id, data)
    return {"data": shot.model_dump(), "error": None}


@router.get("/shots/{shot_id}", response_model=dict)
async def get_shot(
    shot_id: UUID,
    service: ShotService = Depends(get_shot_service),
):
    shot = await service.get(shot_id)
    return {"data": shot.model_dump(), "error": None}


@router.patch("/shots/{shot_id}", response_model=dict)
async def update_shot(
    shot_id: UUID,
    data: ShotUpdate,
    service: ShotService = Depends(get_shot_service),
):
    shot = await service.update(shot_id, data)
    return {"data": shot.model_dump(), "error": None}


@router.delete("/shots/{shot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shot(
    shot_id: UUID,
    service: ShotService = Depends(get_shot_service),
):
    await service.delete(shot_id)


@router.patch("/scenes/{scene_id}/shots/reorder", response_model=dict)
async def reorder_shots(
    scene_id: UUID,
    body: dict,
    service: ShotService = Depends(get_shot_service),
):
    shot_ids = [UUID(id) for id in body["shot_ids"]]
    shots = await service.reorder(scene_id, shot_ids)
    return {"data": [s.model_dump() for s in shots], "error": None}


@router.post("/shots/{shot_id}/generate-background", response_model=dict)
async def generate_shot_background(
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate a background image for the shot's scene."""
    shot_result = await db.execute(select(ShotModel).where(ShotModel.id == shot_id))
    shot = shot_result.scalar_one_or_none()
    if not shot:
        raise NotFoundException(f"Shot {shot_id} not found")

    bg_service = BackgroundGenService(db)
    png, prompt = await bg_service.generate_for_scene(shot.scene_id)

    scene_result = await db.execute(select(SceneModel).where(SceneModel.id == shot.scene_id))
    scene = scene_result.scalar_one_or_none()

    asset = await save_generated_asset(
        db=db,
        project_id=scene.project_id if scene else shot_id,
        asset_type=AssetType.BACKGROUND.value,
        filename=f"bg_shot_{shot_id}.png",
        data=png,
        metadata={"prompt": prompt, "shot_id": str(shot_id), "scene_id": str(shot.scene_id)},
    )

    shot.background_asset_id = asset.id
    await db.commit()

    return {"data": {"asset_id": str(asset.id), "shot_id": str(shot_id), "prompt": prompt}, "error": None}


@router.post("/shots/{shot_id}/generate-keyframe", response_model=dict)
async def generate_shot_keyframe(
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate a keyframe image for a shot."""
    shot_result = await db.execute(select(ShotModel).where(ShotModel.id == shot_id))
    shot = shot_result.scalar_one_or_none()
    if not shot:
        raise NotFoundException(f"Shot {shot_id} not found")

    kf_service = KeyframeGenService(db)
    png, prompt = await kf_service.generate_for_shot(shot_id)

    scene_result = await db.execute(select(SceneModel).where(SceneModel.id == shot.scene_id))
    scene = scene_result.scalar_one_or_none()

    asset = await save_generated_asset(
        db=db,
        project_id=scene.project_id if scene else shot_id,
        asset_type=AssetType.KEYFRAME.value,
        filename=f"kf_shot_{shot_id}.png",
        data=png,
        metadata={"prompt": prompt, "shot_id": str(shot_id), "scene_id": str(shot.scene_id)},
    )

    shot.keyframe_asset_id = asset.id
    shot.generation_prompt = prompt
    shot.status = "keyframe_generated"
    await db.commit()

    return {"data": {"asset_id": str(asset.id), "shot_id": str(shot_id), "prompt": prompt}, "error": None}


@router.post("/scenes/{scene_id}/generate-all-keyframes", response_model=dict)
async def generate_scene_all_keyframes(
    scene_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate keyframes for all shots in a scene."""
    shot_result = await db.execute(
        select(ShotModel).where(ShotModel.scene_id == scene_id).order_by(ShotModel.order_index)
    )
    shots = shot_result.scalars().all()
    if not shots:
        raise NotFoundException(f"No shots found for scene {scene_id}")

    kf_service = KeyframeGenService(db)
    generated = 0
    for shot in shots:
        try:
            png, prompt = await kf_service.generate_for_shot(shot.id)
            scene_result = await db.execute(select(SceneModel).where(SceneModel.id == scene_id))
            scene = scene_result.scalar_one_or_none()
            asset = await save_generated_asset(
                db=db,
                project_id=scene.project_id if scene else scene_id,
                asset_type=AssetType.KEYFRAME.value,
                filename=f"kf_shot_{shot.id}.png",
                data=png,
                metadata={"prompt": prompt, "shot_id": str(shot.id), "scene_id": str(scene_id)},
            )
            shot.keyframe_asset_id = asset.id
            shot.generation_prompt = prompt
            shot.status = "keyframe_generated"
            generated += 1
        except Exception:
            pass
    await db.commit()
    return {"data": {"generated": generated, "total": len(shots)}, "error": None}


@router.post("/shots/{shot_id}/generate-audio", response_model=dict)
async def generate_shot_audio(
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate narration audio for a shot via TTS."""
    shot_result = await db.execute(select(ShotModel).where(ShotModel.id == shot_id))
    shot = shot_result.scalar_one_or_none()
    if not shot:
        raise NotFoundException(f"Shot {shot_id} not found")

    scene_result = await db.execute(select(SceneModel).where(SceneModel.id == shot.scene_id))
    scene = scene_result.scalar_one_or_none()

    tts = TTSService(db=db)
    audio_bytes, text = await tts.generate_for_shot(shot_id)
    voice = shot.audio.voice_profile or "vi-VN-NamMinhNeural"

    asset = await save_generated_asset(
        db=db,
        project_id=scene.project_id if scene else shot_id,
        asset_type=AssetType.AUDIO.value,
        filename=f"audio_shot_{shot_id}.mp3",
        data=audio_bytes,
        metadata={"text": text, "shot_id": str(shot_id), "voice": voice},
    )

    shot.audio_asset_id = asset.id
    await db.commit()

    return {"data": {"asset_id": str(asset.id), "shot_id": str(shot_id), "text": text}, "error": None}


@router.post("/scenes/{scene_id}/generate-all-audio", response_model=dict)
async def generate_scene_all_audio(
    scene_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate audio for all shots in a scene."""
    shot_result = await db.execute(
        select(ShotModel).where(ShotModel.scene_id == scene_id).order_by(ShotModel.order_index)
    )
    shots = shot_result.scalars().all()
    if not shots:
        raise NotFoundException(f"No shots found for scene {scene_id}")

    tts = TTSService(db=db)
    scene_result = await db.execute(select(SceneModel).where(SceneModel.id == scene_id))
    scene = scene_result.scalar_one_or_none()
    generated = 0
    for shot in shots:
        try:
            audio_bytes, text = await tts.generate_for_shot(shot.id)
            voice = shot.audio.voice_profile or "vi-VN-NamMinhNeural"
            asset = await save_generated_asset(
                db=db,
                project_id=scene.project_id if scene else scene_id,
                asset_type=AssetType.AUDIO.value,
                filename=f"audio_shot_{shot.id}.mp3",
                data=audio_bytes,
                metadata={"text": text, "shot_id": str(shot.id), "voice": voice},
            )
            shot.audio_asset_id = asset.id
            generated += 1
        except Exception:
            pass
    await db.commit()
    return {"data": {"generated": generated, "total": len(shots)}, "error": None}


@router.post("/scenes/{scene_id}/export", response_model=dict, status_code=status.HTTP_201_CREATED)
async def export_scene(
    scene_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Export scene as MP4 video from keyframes + audio."""
    scene_result = await db.execute(select(SceneModel).where(SceneModel.id == scene_id))
    scene = scene_result.scalar_one_or_none()
    if not scene:
        raise NotFoundException(f"Scene {scene_id} not found")

    export_service = ExportService(db)
    mp4_bytes, filename = await export_service.export_scene(scene_id)

    asset = await save_generated_asset(
        db=db,
        project_id=scene.project_id,
        asset_type=AssetType.EXPORT.value,
        filename=filename,
        data=mp4_bytes,
        metadata={"scene_id": str(scene_id), "mime_type": "video/mp4"},
    )

    return {
        "data": {
            "asset_id": str(asset.id),
            "scene_id": str(scene_id),
            "url": f"/storage/asset/{asset.id}",
        },
        "error": None,
    }
