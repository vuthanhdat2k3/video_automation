from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.story import StoryBibleRequest

from app.database import get_db
from app.exceptions import NotFoundException
from app.models.character import CharacterModel
from app.models.project import ProjectModel
from app.models.scene import SceneModel
from app.models.shot import ShotModel
from app.services.story import StoryBibleService

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


@router.post("/projects/{project_id}/story/materialize", status_code=status.HTTP_201_CREATED)
async def materialize_story_bible(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Create SceneModel + ShotModel records from story bible scene_breakdowns."""
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundException(f"Project {project_id} not found")
    if not project.story_json:
        raise NotFoundException(f"Project {project_id} has no story bible")

    breakdowns = project.story_json.get("scene_breakdowns", [])
    if not breakdowns:
        return {"data": {"created_scenes": 0, "created_shots": 0}, "error": None}

    char_result = await db.execute(
        select(CharacterModel).where(CharacterModel.project_id == project_id)
    )
    char_map = {c.name: c.id for c in char_result.scalars().all()}

    scenes_created = 0
    shots_created = 0
    for sb in breakdowns:
        continuity = {}
        if sb.get("characters_present"):
            uuids = [str(char_map[n]) for n in sb["characters_present"] if n in char_map]
            if uuids:
                continuity["characters_present"] = uuids
        if sb.get("location"):
            continuity["location"] = sb["location"]
        if sb.get("emotional_beat"):
            continuity["mood"] = sb["emotional_beat"]

        is_intro = sb.get("scene_order", 0) == 0 and sb.get("episode_number", 1) == 1

        scene = SceneModel(
            project_id=project_id,
            title=sb.get("title", f"Scene {sb.get('scene_order', 0)}"),
            description=sb.get("description", ""),
            duration_seconds=sb.get("duration_seconds", 10.0),
            order_index=sb.get("scene_order", 0),
            episode_number=sb.get("episode_number"),
            continuity_json=continuity,
        )
        db.add(scene)
        await db.flush()
        scenes_created += 1

        shot = ShotModel(
            scene_id=scene.id,
            order_index=0,
            duration_seconds=sb.get("duration_seconds", 10.0),
            shot_type="cinematic_intro" if is_intro else "dialogue",
        )
        db.add(shot)
        shots_created += 1

    await db.commit()
    return {"data": {"created_scenes": scenes_created, "created_shots": shots_created}, "error": None}
