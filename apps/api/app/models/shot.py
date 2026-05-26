from uuid import uuid4
from datetime import datetime

from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from ai_2d_shared.shot import CameraConfig, MotionConfig, AudioConfig


class ShotModel(Base):
    __tablename__ = "shots"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    scene_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("4.0"))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    shot_type: Mapped[str] = mapped_column(String(30), nullable=False, server_default="dialogue")
    camera_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    motion_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    audio_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    background_asset_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    keyframe_asset_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    audio_asset_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    video_export_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_params: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    overlay_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def camera(self) -> CameraConfig:
        return CameraConfig(**self.camera_json) if self.camera_json else CameraConfig()

    @property
    def motion(self) -> MotionConfig:
        return MotionConfig(**self.motion_json) if self.motion_json else MotionConfig()

    @property
    def audio(self) -> AudioConfig:
        return AudioConfig(**self.audio_json) if self.audio_json else AudioConfig()
