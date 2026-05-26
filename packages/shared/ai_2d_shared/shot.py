from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .enums import ShotType


class CameraConfig(BaseModel):
    angle: str = "medium"  # aerial, high, eye-level, low, dutch
    framing: str = "medium"  # extreme-wide, wide, medium, close-up, extreme-close-up
    movement: str = "static"  # static, pan, tilt, dolly, track, crane, handheld
    lens: str | None = None


class MotionConfig(BaseModel):
    animation_style: str = "live2d"  # live2d, cutout, frame_by_frame, puppet
    easing: str = "ease_in_out"  # linear, ease_in, ease_out, ease_in_out
    fps: int = 24


class AudioConfig(BaseModel):
    voice_profile: str | None = None
    background_music: str | None = None
    sound_effects: list[str] = Field(default_factory=list)
    volume: float = 1.0


class ShotCreate(BaseModel):
    scene_id: UUID
    order_index: int
    duration_seconds: float = 4.0
    description: str | None = None
    shot_type: ShotType = ShotType.DIALOGUE
    camera: CameraConfig = Field(default_factory=CameraConfig)
    motion: MotionConfig = Field(default_factory=MotionConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)


class ShotUpdate(BaseModel):
    order_index: int | None = None
    duration_seconds: float | None = None
    description: str | None = None
    shot_type: ShotType | None = None
    camera: CameraConfig | None = None
    motion: MotionConfig | None = None
    audio: AudioConfig | None = None


class ShotRead(BaseModel):
    id: UUID
    scene_id: UUID
    order_index: int
    duration_seconds: float
    description: str | None
    shot_type: ShotType
    camera: CameraConfig
    motion: MotionConfig
    audio: AudioConfig
    background_asset_id: UUID | None = None
    keyframe_asset_id: UUID | None = None
    audio_asset_id: UUID | None = None
    video_export_id: UUID | None = None
    generation_prompt: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
