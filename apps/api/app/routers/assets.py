from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.enums import AssetType

from app.database import get_db
from app.exceptions import NotFoundException
from app.models.asset import AssetModel
from app.models.character import CharacterModel
from app.models.project import ProjectModel
from app.services.storage import StorageManager
from app.config import settings

router = APIRouter()

# ---- Helpers ----


def get_storage() -> StorageManager:
    return StorageManager(settings.storage_root)


async def save_generated_asset(
    db: AsyncSession,
    project_id: UUID,
    filename: str,
    data: bytes,
    metadata: dict | None = None,
) -> AssetModel:
    """Save generated image bytes as an asset record + file. Returns AssetModel."""
    storage = get_storage()
    rel_path = storage.save_asset(project_id, "characters", filename, data)
    asset = AssetModel(
        project_id=project_id,
        type=AssetType.CHARACTER.value,
        filename=filename,
        path=str(rel_path),
        metadata_json=metadata or {},
    )
    db.add(asset)
    await db.flush()
    return asset


# ---- Routes ----


@router.get("/characters/{character_id}/assets", response_model=dict)
async def list_character_assets(
    character_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CharacterModel).where(CharacterModel.id == character_id))
    character = result.scalar_one_or_none()
    if not character:
        raise NotFoundException(f"Character {character_id} not found")

    query = (
        select(AssetModel)
        .where(AssetModel.project_id == character.project_id)
        .where(AssetModel.type == AssetType.CHARACTER.value)
        .order_by(AssetModel.created_at.desc())
    )
    result = await db.execute(query)
    assets = result.scalars().all()
    return {"data": [_asset_to_dict(a) for a in assets], "error": None}


@router.get("/projects/{project_id}/assets", response_model=dict)
async def list_project_assets(
    project_id: UUID,
    type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    if not result.scalar_one_or_none():
        raise NotFoundException(f"Project {project_id} not found")

    query = select(AssetModel).where(AssetModel.project_id == project_id)
    if type:
        query = query.where(AssetModel.type == type)
    query = query.order_by(AssetModel.created_at.desc())

    result = await db.execute(query)
    assets = result.scalars().all()
    return {"data": [_asset_to_dict(a) for a in assets], "error": None}


@router.get("/assets/{asset_id}", response_model=dict)
async def get_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AssetModel).where(AssetModel.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise NotFoundException(f"Asset {asset_id} not found")
    return {"data": _asset_to_dict(asset), "error": None}


@router.get("/assets/{asset_id}/download")
async def download_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageManager = Depends(get_storage),
):
    result = await db.execute(select(AssetModel).where(AssetModel.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise NotFoundException(f"Asset {asset_id} not found")

    # If S3 cloud storage is enabled, redirect directly to Supabase Public CDN for high-speed delivery
    public_url = storage.get_public_url(asset.project_id, asset.path)
    if public_url:
        return RedirectResponse(url=public_url)

    file_path = storage.get_asset_path(asset.project_id, asset.path)
    if not file_path.exists():
        raise NotFoundException(f"Asset file not found on disk")

    return FileResponse(
        path=file_path,
        filename=asset.filename,
        media_type=asset.metadata_json.get("mime_type", "application/octet-stream"),
    )


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageManager = Depends(get_storage),
):
    result = await db.execute(select(AssetModel).where(AssetModel.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise NotFoundException(f"Asset {asset_id} not found")

    storage.delete_asset(asset.project_id, asset.path)
    await db.delete(asset)
    await db.commit()


def _asset_to_dict(asset: AssetModel) -> dict:
    return {
        "id": str(asset.id),
        "project_id": str(asset.project_id),
        "type": asset.type,
        "filename": asset.filename,
        "path": asset.path,
        "metadata": asset.metadata_json,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
    }
