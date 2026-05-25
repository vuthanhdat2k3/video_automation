from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.project import ProjectCreate, ProjectRead, ProjectUpdate

from app.database import get_db
from app.services.project import ProjectService
from app.services.storage import StorageManager
from app.config import settings

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
