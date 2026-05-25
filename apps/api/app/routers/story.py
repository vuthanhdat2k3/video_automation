from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.story import StoryBibleRequest

from app.database import get_db
from app.exceptions import NotFoundException
from app.models.project import ProjectModel
from app.services.story import StoryBibleService
from sqlalchemy import select

router = APIRouter()


def get_story_service(db: AsyncSession = Depends(get_db)) -> StoryBibleService:
    return StoryBibleService(db=db)


@router.post("/projects/{project_id}/story/generate", status_code=status.HTTP_201_CREATED)
async def generate_story_bible(
    project_id: UUID,
    request: StoryBibleRequest,
    db: AsyncSession = Depends(get_db),
    service: StoryBibleService = Depends(get_story_service),
):
    # Verify project exists
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    if not result.scalar_one_or_none():
        raise NotFoundException(f"Project {project_id} not found")

    bible = await service.generate_story_bible(request)
    await service.save_bible_to_project(project_id, bible)

    return {"data": bible.model_dump(), "error": None}


@router.get("/projects/{project_id}/story")
async def get_story_bible(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundException(f"Project {project_id} not found")
    if not project.story_json:
        return {"data": None, "error": None}
    return {"data": project.story_json, "error": None}


@router.post("/projects/{project_id}/story/regenerate")
async def regenerate_story_bible(
    project_id: UUID,
    request: StoryBibleRequest,
    db: AsyncSession = Depends(get_db),
    service: StoryBibleService = Depends(get_story_service),
):
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    if not result.scalar_one_or_none():
        raise NotFoundException(f"Project {project_id} not found")

    bible = await service.generate_story_bible(request)
    await service.save_bible_to_project(project_id, bible)

    return {"data": bible.model_dump(), "error": None}
