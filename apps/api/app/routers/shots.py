"""Shots router — CRUD + generation dispatch."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.shot import ShotCreate, ShotUpdate

from app.database import get_db
from app.exceptions import NotFoundException
from app.models.scene import SceneModel
from app.models.shot import ShotModel
from app.models.job import JobModel
from app.services.shot import ShotService
from app.services.queue import dispatch_job, get_queue
from app.services.batch import BatchJobService

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
    """Dispatch background generation job."""
    shot_result = await db.execute(select(ShotModel).where(ShotModel.id == shot_id))
    shot = shot_result.scalar_one_or_none()
    if not shot:
        raise NotFoundException(f"Shot {shot_id} not found")

    scene_result = await db.execute(select(SceneModel).where(SceneModel.id == shot.scene_id))
    scene = scene_result.scalar_one_or_none()

    job = await dispatch_job(
        db=db,
        project_id=scene.project_id,
        job_type="generate_background",
        task_name="run_generate_background",
        input_data={"shot_id": str(shot_id), "scene_id": str(shot.scene_id)},
    )

    return {"data": {"job_id": str(job.id)}, "error": None}


@router.post("/shots/{shot_id}/generate-keyframe", response_model=dict)
async def generate_shot_keyframe(
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Dispatch keyframe generation job."""
    shot_result = await db.execute(select(ShotModel).where(ShotModel.id == shot_id))
    shot = shot_result.scalar_one_or_none()
    if not shot:
        raise NotFoundException(f"Shot {shot_id} not found")

    scene_result = await db.execute(select(SceneModel).where(SceneModel.id == shot.scene_id))
    scene = scene_result.scalar_one_or_none()

    job = await dispatch_job(
        db=db,
        project_id=scene.project_id,
        job_type="generate_keyframe",
        task_name="run_generate_keyframe",
        input_data={"shot_id": str(shot_id)},
    )

    return {"data": {"job_id": str(job.id)}, "error": None}


@router.post("/scenes/{scene_id}/generate-all-keyframes", response_model=dict)
async def generate_scene_all_keyframes(
    scene_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Dispatch keyframe generation for all shots in a scene (batched)."""
    shot_result = await db.execute(
        select(ShotModel).where(ShotModel.scene_id == scene_id).order_by(ShotModel.order_index)
    )
    shots = shot_result.scalars().all()
    if not shots:
        raise NotFoundException(f"No shots found for scene {scene_id}")

    scene_result = await db.execute(select(SceneModel).where(SceneModel.id == scene_id))
    scene = scene_result.scalar_one_or_none()

    batch_svc = BatchJobService(db)
    children = [
        {"job_type": "generate_keyframe", "input_data": {"shot_id": str(shot.id)}}
        for shot in shots
    ]
    parent, child_jobs = await batch_svc.create_batch(
        project_id=scene.project_id,
        batch_type="generate_all_keyframes",
        children=children,
    )

    queue = await get_queue()
    for child, shot in zip(child_jobs, shots):
        await queue.enqueue_job(
            "run_generate_keyframe",
            _job_id=str(child.id),
            project_id=str(scene.project_id),
            shot_id=str(shot.id),
        )

    return {"data": {"batch_id": str(parent.id), "job_ids": [str(c.id) for c in child_jobs]}, "error": None}


@router.post("/shots/{shot_id}/generate-audio", response_model=dict)
async def generate_shot_audio(
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Dispatch audio generation job."""
    shot_result = await db.execute(select(ShotModel).where(ShotModel.id == shot_id))
    shot = shot_result.scalar_one_or_none()
    if not shot:
        raise NotFoundException(f"Shot {shot_id} not found")

    scene_result = await db.execute(select(SceneModel).where(SceneModel.id == shot.scene_id))
    scene = scene_result.scalar_one_or_none()

    job = await dispatch_job(
        db=db,
        project_id=scene.project_id,
        job_type="generate_audio",
        task_name="run_generate_audio",
        input_data={"shot_id": str(shot_id)},
    )

    return {"data": {"job_id": str(job.id)}, "error": None}


@router.post("/scenes/{scene_id}/generate-all-audio", response_model=dict)
async def generate_scene_all_audio(
    scene_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Dispatch audio generation for all shots in a scene (batched)."""
    shot_result = await db.execute(
        select(ShotModel).where(ShotModel.scene_id == scene_id).order_by(ShotModel.order_index)
    )
    shots = shot_result.scalars().all()
    if not shots:
        raise NotFoundException(f"No shots found for scene {scene_id}")

    scene_result = await db.execute(select(SceneModel).where(SceneModel.id == scene_id))
    scene = scene_result.scalar_one_or_none()

    batch_svc = BatchJobService(db)
    children = [
        {"job_type": "generate_audio", "input_data": {"shot_id": str(shot.id)}}
        for shot in shots
    ]
    parent, child_jobs = await batch_svc.create_batch(
        project_id=scene.project_id,
        batch_type="generate_all_audio",
        children=children,
    )

    queue = await get_queue()
    for child, shot in zip(child_jobs, shots):
        await queue.enqueue_job(
            "run_generate_audio",
            _job_id=str(child.id),
            project_id=str(scene.project_id),
            shot_id=str(shot.id),
        )

    return {"data": {"batch_id": str(parent.id), "job_ids": [str(c.id) for c in child_jobs]}, "error": None}


@router.post("/scenes/{scene_id}/export", response_model=dict, status_code=status.HTTP_201_CREATED)
async def export_scene(
    scene_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Dispatch export job."""
    scene_result = await db.execute(select(SceneModel).where(SceneModel.id == scene_id))
    scene = scene_result.scalar_one_or_none()
    if not scene:
        raise NotFoundException(f"Scene {scene_id} not found")

    job = await dispatch_job(
        db=db,
        project_id=scene.project_id,
        job_type="export",
        task_name="run_export_scene",
        input_data={"scene_id": str(scene_id)},
    )

    return {
        "data": {"job_id": str(job.id), "scene_id": str(scene_id)},
        "error": None,
    }


@router.post("/shots/{shot_id}/generate-lipsync", response_model=dict)
async def generate_shot_lipsync(
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Dispatch lip sync generation for a shot (auto-depends on audio job)."""
    shot_result = await db.execute(select(ShotModel).where(ShotModel.id == shot_id))
    shot = shot_result.scalar_one_or_none()
    if not shot:
        raise NotFoundException(f"Shot {shot_id} not found")

    scene_result = await db.execute(select(SceneModel).where(SceneModel.id == shot.scene_id))
    scene = scene_result.scalar_one_or_none()

    # Auto-dependency: find most recent completed audio job for this shot
    from app.models.job import JobModel
    audio_job_result = await db.execute(
        select(JobModel)
        .where(JobModel.type == "generate_audio")
        .where(JobModel.status == "completed")
        .where(JobModel.input_json["shot_id"].astext == str(shot_id))
        .order_by(JobModel.created_at.desc())
        .limit(1)
    )
    audio_job = audio_job_result.scalar_one_or_none()

    job = await dispatch_job(
        db=db,
        project_id=scene.project_id,
        job_type="lipsync",
        task_name="run_lipsync_shot",
        input_data={"shot_id": str(shot_id)},
        depends_on=audio_job.id if audio_job else None,
    )

    return {"data": {"job_id": str(job.id)}, "error": None}
