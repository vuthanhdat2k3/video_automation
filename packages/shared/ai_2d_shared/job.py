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
    input_data: dict = Field(alias="input_json")
    output_data: dict | None = Field(alias="output_json", default=None)
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
