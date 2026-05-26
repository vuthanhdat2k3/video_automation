from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.scene import ContinuityState, SceneCreate, SceneRead, SceneUpdate

from app.database import get_db
from app.exceptions import NotFoundException
from app.models.project import ProjectModel
from app.models.scene import SceneModel
from app.models.shot import ShotModel
from app.services.scene import SceneService
from app.services.shot import ShotService
from app.services.timeline import compute_scene_timeline
from sqlalchemy import select

router = APIRouter()


def get_scene_service(db: AsyncSession = Depends(get_db)) -> SceneService:
    return SceneService(db=db)


def get_shot_service(db: AsyncSession = Depends(get_db)) -> ShotService:
    return ShotService(db=db)


@router.get("/projects/{project_id}/scenes", response_model=dict)
async def list_scenes(
    project_id: UUID,
    episode: int | None = None,
    db: AsyncSession = Depends(get_db),
    service: SceneService = Depends(get_scene_service),
):
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    if not result.scalar_one_or_none():
        raise NotFoundException(f"Project {project_id} not found")
    scenes = await service.list_by_project(project_id, episode=episode)
    return {"data": [s.model_dump() for s in scenes], "error": None}


@router.post("/projects/{project_id}/scenes", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_scene(
    project_id: UUID,
    data: SceneCreate,
    db: AsyncSession = Depends(get_db),
    service: SceneService = Depends(get_scene_service),
):
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    if not result.scalar_one_or_none():
        raise NotFoundException(f"Project {project_id} not found")

    if data.project_id != project_id:
        data.project_id = project_id

    scene = await service.create(project_id, data)
    return {"data": scene.model_dump(), "error": None}


@router.get("/scenes/{scene_id}", response_model=dict)
async def get_scene(
    scene_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: SceneService = Depends(get_scene_service),
    shot_service: ShotService = Depends(get_shot_service),
):
    scene = await service.get(scene_id)
    shots = await shot_service.list_by_scene(scene_id)
    result = scene.model_dump()
    result["shots"] = [s.model_dump() for s in shots]
    return {"data": result, "error": None}


@router.patch("/scenes/{scene_id}", response_model=dict)
async def update_scene(
    scene_id: UUID,
    data: SceneUpdate,
    service: SceneService = Depends(get_scene_service),
):
    scene = await service.update(scene_id, data)
    return {"data": scene.model_dump(), "error": None}


@router.delete("/scenes/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scene(
    scene_id: UUID,
    service: SceneService = Depends(get_scene_service),
):
    await service.delete(scene_id)


@router.patch("/projects/{project_id}/scenes/reorder", response_model=dict)
async def reorder_scenes(
    project_id: UUID,
    body: dict,
    service: SceneService = Depends(get_scene_service),
):
    scene_ids = [UUID(id) for id in body["scene_ids"]]
    scenes = await service.reorder(project_id, scene_ids)
    return {"data": [s.model_dump() for s in scenes], "error": None}


@router.get("/projects/{project_id}/timeline", response_model=dict)
async def project_timeline(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    shot_service: ShotService = Depends(get_shot_service),
    service: SceneService = Depends(get_scene_service),
):
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    if not result.scalar_one_or_none():
        raise NotFoundException(f"Project {project_id} not found")

    scenes = await service.list_by_project(project_id)
    total_duration = 0.0
    scene_timelines = []
    for s in scenes:
        shots = await shot_service.list_by_scene(s.id)
        timeline = compute_scene_timeline(shots)
        total_duration += timeline["total_duration"]
        scene_timelines.append({
            "scene": s.model_dump(),
            "start_at": timeline["start_at"],
            "shots": timeline["shots"],
        })

    return {
        "data": {
            "total_duration": total_duration,
            "scene_count": len(scenes),
            "scenes": scene_timelines,
        },
        "error": None,
    }


@router.get("/scenes/{scene_id}/timeline", response_model=dict)
async def scene_timeline(
    scene_id: UUID,
    shot_service: ShotService = Depends(get_shot_service),
):
    shots = await shot_service.list_by_scene(scene_id)
    timeline = compute_scene_timeline(shots)
    return {"data": timeline, "error": None}
