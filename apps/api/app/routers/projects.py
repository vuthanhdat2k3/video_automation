from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.project import ProjectCreate, ProjectRead, ProjectUpdate

from app.database import get_db
from app.services.project import ProjectService
from app.services.storage import StorageManager
from app.services.queue import dispatch_job, get_queue
from app.services.batch import BatchJobService
from app.config import settings
from app.models.scene import SceneModel
from app.exceptions import NotFoundException
from sqlalchemy import select

router = APIRouter()


def get_storage() -> StorageManager:
    return StorageManager(settings.storage_root)


def get_project_service(
    db: AsyncSession = Depends(get_db),
    storage: StorageManager = Depends(get_storage),
) -> ProjectService:
    return ProjectService(db, storage)


@router.post("/projects", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    service: ProjectService = Depends(get_project_service),
):
    project = await service.create_project(data)
    return {"data": project.model_dump(), "error": None}


@router.get("/projects", response_model=dict)
async def list_projects(
    service: ProjectService = Depends(get_project_service),
):
    projects = await service.list_projects()
    return {"data": [p.model_dump() for p in projects], "error": None}


@router.get("/projects/{project_id}", response_model=dict)
async def get_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
):
    project = await service.get_project(project_id)
    return {"data": project.model_dump(), "error": None}


@router.patch("/projects/{project_id}", response_model=dict)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    service: ProjectService = Depends(get_project_service),
):
    project = await service.update_project(project_id, data)
    return {"data": project.model_dump(), "error": None}


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
):
    await service.delete_project(project_id)


@router.post("/projects/{project_id}/export", response_model=dict, status_code=status.HTTP_201_CREATED)
async def export_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Export entire project: batch dispatch all scene exports."""
    scene_result = await db.execute(
        select(SceneModel).where(SceneModel.project_id == project_id)
        .order_by(SceneModel.order_index)
    )
    scenes = scene_result.scalars().all()
    if not scenes:
        raise NotFoundException(f"Project {project_id} has no scenes")

    batch_svc = BatchJobService(db)
    children = [
        {"task_name": "run_export_scene", "job_type": "export",
         "input_data": {"scene_id": str(s.id)}}
        for s in scenes
    ]
    parent, child_jobs = await batch_svc.create_batch(
        project_id=project_id, batch_type="export_project", children=children,
    )

    queue = await get_queue()
    for child, scene in zip(child_jobs, scenes):
        await queue.enqueue_job(
            "run_export_scene", _job_id=str(child.id),
            project_id=str(project_id), scene_id=str(scene.id),
        )

    concat_job = await dispatch_job(
        db=db, project_id=project_id,
        job_type="export", task_name="run_concat_project",
        input_data={},
        depends_on=parent.id,
    )

    return {
        "data": {
            "batch_id": str(parent.id),
            "concat_job_id": str(concat_job.id),
            "scene_count": len(scenes),
        },
        "error": None,
    }
