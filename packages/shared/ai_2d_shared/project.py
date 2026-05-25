from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import Status, Style


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    style: Style = Style.TWO_D_CHINESE_DONGHUA
    aspect_ratio: str = Field(default="9:16", pattern=r"^\d+:\d+$")
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    style: Style | None = None
    aspect_ratio: str | None = Field(default=None, pattern=r"^\d+:\d+$")
    description: str | None = None
    status: Status | None = None


class ProjectRead(BaseModel):
    id: UUID
    name: str
    style: Style
    aspect_ratio: str
    description: str | None
    status: Status
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
