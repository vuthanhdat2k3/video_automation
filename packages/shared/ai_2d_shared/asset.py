from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .enums import AssetType


class AssetMetadata(BaseModel):
    width: int | None = None
    height: int | None = None
    file_size_bytes: int | None = None
    mime_type: str | None = None
    content_hash: str | None = None
    source: str | None = None  # generated, uploaded, external
    tags: list[str] = Field(default_factory=list)


class AssetCreate(BaseModel):
    project_id: UUID
    type: AssetType
    filename: str = Field(..., min_length=1, max_length=255)
    metadata: AssetMetadata = Field(default_factory=AssetMetadata)


class AssetRead(BaseModel):
    id: UUID
    project_id: UUID
    type: AssetType
    filename: str
    path: str
    metadata: AssetMetadata
    created_at: datetime

    model_config = {"from_attributes": True}
