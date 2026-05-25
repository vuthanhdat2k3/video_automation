from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CharacterDNA(BaseModel):
    """Core identity traits that define a character's visual appearance and personality."""
    age: int | None = None
    gender: str | None = None
    hair_style: str | None = None
    hair_color: str | None = None
    eye_shape: str | None = None
    eye_color: str | None = None
    face_shape: str | None = None
    skin_tone: str | None = None
    height: str | None = None
    build: str | None = None
    clothing_style: str | None = None
    distinctive_features: list[str] = Field(default_factory=list)
    personality_traits: list[str] = Field(default_factory=list)


class CharacterCreate(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    role: str | None = None
    character_dna: CharacterDNA = Field(default_factory=CharacterDNA)


class CharacterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = None
    character_dna: CharacterDNA | None = None
    reference_asset_id: UUID | None = None


class CharacterRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    role: str | None
    character_dna: CharacterDNA
    reference_asset_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
