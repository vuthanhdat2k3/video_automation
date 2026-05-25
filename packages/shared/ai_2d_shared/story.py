from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .enums import Style


class WorldInfo(BaseModel):
    name: str
    era: str
    location: str
    society: str
    atmosphere: str
    rules: list[str] = Field(default_factory=list)
    factions: list[str] = Field(default_factory=list)


class PowerSystem(BaseModel):
    name: str = ""
    stages: list[str] = Field(default_factory=list)
    source: str | None = None
    special_abilities: list[str] = Field(default_factory=list)


class Tone(BaseModel):
    primary: str = ""
    pacing: str = "mixed"
    emotional_range: list[str] = Field(default_factory=list)


class EpisodeOutline(BaseModel):
    episode_number: int
    title: str
    summary: str
    key_events: list[str | dict[str, Any]] = Field(default_factory=list)
    character_focus: list[str] = Field(default_factory=list)
    cliffhanger: str | None = None


class SceneBreakdown(BaseModel):
    episode_number: int
    scene_order: int
    title: str
    description: str
    characters_present: list[str] = Field(default_factory=list)
    location: str | None = None
    duration_seconds: float = 10.0
    emotional_beat: str | None = None


class StoryBible(BaseModel):
    project_id: UUID
    world: WorldInfo = Field(default_factory=WorldInfo)
    power_system: PowerSystem = Field(default_factory=PowerSystem)
    tone: Tone = Field(default_factory=Tone)
    characters: list[dict] = Field(default_factory=list)
    episodes: list[EpisodeOutline] = Field(default_factory=list)
    scene_breakdowns: list[SceneBreakdown] = Field(default_factory=list)


class StoryBibleRequest(BaseModel):
    concept: str = Field(..., min_length=10, max_length=5000)
    style: Style = Style.TWO_D_CHINESE_DONGHUA
    target_episodes: int = Field(default=1, ge=1, le=10)
    episode_duration_minutes: float = Field(default=1.5, ge=0.5, le=10)
    language: str = Field(default="vietnamese")
    constraints: list[str] | None = None


class CharacterSheet(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: str | None = None
    appearance: str | None = None
    personality: str | None = None
    backstory: str | None = None
    age: int | None = None
    gender: str | None = None
    power_level: str | None = None
    relationships: list[str] = Field(default_factory=list)
    visual_cues: list[str] = Field(default_factory=list)
    style_tokens: list[str] = Field(default_factory=list)
