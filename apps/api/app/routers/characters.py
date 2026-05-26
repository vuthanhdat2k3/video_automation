from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.character import CharacterDNA, CharacterUpdate

from app.database import get_db
from app.exceptions import NotFoundException
from app.models.character import CharacterModel
from app.models.project import ProjectModel
from app.services.asset_utils import save_generated_asset
from app.services.character import CharacterService
from app.services.image_gen import ImageGenService

router = APIRouter()


class CharacterCreateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: str | None = None
    character_dna: CharacterDNA = Field(default_factory=CharacterDNA)


class GenerateImageRequest(BaseModel):
    expression: str = "neutral"
    pose: str = "portrait"
    width: int = 1024
    height: int = 1536
    steps: int = 25
    cfg: float = 5.0
    seed: int | None = None


def get_character_service(db: AsyncSession = Depends(get_db)) -> CharacterService:
    return CharacterService(db=db)


def get_image_gen_service() -> ImageGenService:
    return ImageGenService()


@router.get("/projects/{project_id}/characters", response_model=dict)
async def list_characters(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: CharacterService = Depends(get_character_service),
):
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    if not result.scalar_one_or_none():
        raise NotFoundException(f"Project {project_id} not found")

    characters = await service.list_by_project(project_id)
    return {"data": [c.model_dump() for c in characters], "error": None}


@router.post("/projects/{project_id}/characters", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_character(
    project_id: UUID,
    data: CharacterCreateBody,
    db: AsyncSession = Depends(get_db),
    service: CharacterService = Depends(get_character_service),
):
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    if not result.scalar_one_or_none():
        raise NotFoundException(f"Project {project_id} not found")

    character = await service.create(project_id, data)
    return {"data": character.model_dump(), "error": None}


@router.get("/characters/{character_id}", response_model=dict)
async def get_character(
    character_id: UUID,
    service: CharacterService = Depends(get_character_service),
):
    character = await service.get(character_id)
    return {"data": character.model_dump(), "error": None}


@router.patch("/characters/{character_id}", response_model=dict)
async def update_character(
    character_id: UUID,
    data: CharacterUpdate,
    service: CharacterService = Depends(get_character_service),
):
    character = await service.update(character_id, data)
    return {"data": character.model_dump(), "error": None}


@router.delete("/characters/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    character_id: UUID,
    service: CharacterService = Depends(get_character_service),
):
    await service.delete(character_id)


@router.post("/characters/{character_id}/generate-image", response_model=dict)
async def generate_character_image(
    character_id: UUID,
    req: GenerateImageRequest,
    db: AsyncSession = Depends(get_db),
    char_service: CharacterService = Depends(get_character_service),
    img_service: ImageGenService = Depends(get_image_gen_service),
):
    character = await char_service.get(character_id)

    png_bytes = await img_service.generate_character_portrait(
        dna=character.character_dna,
        expression=req.expression,
        pose=req.pose,
        seed=req.seed,
        width=req.width,
        height=req.height,
        steps=req.steps,
        cfg=req.cfg,
    )

    # Save as asset attached to project
    asset = await save_generated_asset(
        db=db,
        project_id=character.project_id,
        filename=f"char_{character_id}_{req.expression}.png",
        data=png_bytes,
        metadata={
            "width": req.width,
            "height": req.height,
            "mime_type": "image/png",
            "source": "generated",
            "character_id": str(character_id),
            "expression": req.expression,
            "pose": req.pose,
        },
    )

    # Link to character if no reference asset yet
    result = await db.execute(select(CharacterModel).where(CharacterModel.id == character_id))
    char_model = result.scalar_one_or_none()
    if char_model and char_model.reference_asset_id is None:
        char_model.reference_asset_id = asset.id
        await db.commit()

    return {"data": {"asset_id": str(asset.id), "character_id": str(character_id)}, "error": None}


class GenerateExpressionRequest(BaseModel):
    expression: str = "happy"
    intensity: float = 0.8
    pose: str = "portrait"
    width: int = 1024
    height: int = 1536
    steps: int = 25
    cfg: float = 5.0
    seed: int | None = None


@router.post("/characters/{character_id}/generate-expression", response_model=dict)
async def generate_character_expression(
    character_id: UUID,
    req: GenerateExpressionRequest,
    db: AsyncSession = Depends(get_db),
    char_service: CharacterService = Depends(get_character_service),
    img_service: ImageGenService = Depends(get_image_gen_service),
):
    character = await char_service.get(character_id)

    png_bytes = await img_service.generate_character_portrait(
        dna=character.character_dna,
        expression=req.expression,
        pose=req.pose,
        seed=req.seed or int(datetime.now().timestamp() * 1000) % (2**32),
        width=req.width,
        height=req.height,
        steps=req.steps,
        cfg=req.cfg,
    )

    asset = await save_generated_asset(
        db=db,
        project_id=character.project_id,
        filename=f"char_{character_id}_expr_{req.expression}.png",
        data=png_bytes,
        metadata={
            "width": req.width,
            "height": req.height,
            "mime_type": "image/png",
            "source": "generated",
            "character_id": str(character_id),
            "expression": req.expression,
            "pose": req.pose,
        },
    )

    return {"data": {"asset_id": str(asset.id), "character_id": str(character_id)}, "error": None}


class SetPrimaryAssetRequest(BaseModel):
    asset_id: UUID


@router.post("/characters/{character_id}/set-primary-asset", response_model=dict)
async def set_character_primary_asset(
    character_id: UUID,
    req: SetPrimaryAssetRequest,
    db: AsyncSession = Depends(get_db),
    char_service: CharacterService = Depends(get_character_service),
):
    result = await db.execute(select(CharacterModel).where(CharacterModel.id == character_id))
    char_model = result.scalar_one_or_none()
    if not char_model:
        from app.exceptions import NotFoundException
        raise NotFoundException(f"Character {character_id} not found")

    char_model.reference_asset_id = req.asset_id
    await db.commit()
    await db.refresh(char_model)

    character = await char_service.get(character_id)
    return {"data": character.model_dump(), "error": None}
