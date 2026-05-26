from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.asset import AssetModel
from app.services.storage import StorageManager


_storage: StorageManager | None = None


def _get_storage() -> StorageManager:
    global _storage
    if _storage is None:
        _storage = StorageManager(settings.storage_root)
    return _storage


async def save_generated_asset(
    db: AsyncSession,
    project_id: UUID,
    asset_type: str,
    filename: str,
    data: bytes,
    metadata: dict | None = None,
) -> AssetModel:
    """Save generated image bytes as an asset record + file. Returns AssetModel."""
    storage = _get_storage()
    rel_path = storage.save_asset(project_id, asset_type, filename, data)
    asset = AssetModel(
        project_id=project_id,
        type=asset_type,
        filename=filename,
        path=str(rel_path),
        metadata_json=metadata or {},
    )
    db.add(asset)
    await db.flush()
    return asset
