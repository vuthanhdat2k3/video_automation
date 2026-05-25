from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .enums import JobType, Status


class JobCreate(BaseModel):
    project_id: UUID
    type: JobType
    input_data: dict = Field(default_factory=dict)


class JobRead(BaseModel):
    id: UUID
    project_id: UUID
    type: JobType
    status: Status
    progress: float
    input_data: dict
    output_data: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
