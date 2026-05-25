from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ContinuityState(BaseModel):
    """Tracks character positions, active props, lighting, and mood across a scene."""
    characters_present: list[UUID] = Field(default_factory=list)
    active_props: list[str] = Field(default_factory=list)
    lighting: str | None = None
    mood: str | None = None
    time_of_day: str | None = None
    weather: str | None = None


class SceneCreate(BaseModel):
    project_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    duration_seconds: float | None = None
    continuity: ContinuityState = Field(default_factory=ContinuityState)


class SceneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    duration_seconds: float | None = None
    continuity: ContinuityState | None = None
    order_index: int | None = None


class SceneRead(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    duration_seconds: float | None
    order_index: int
    continuity: ContinuityState
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
