from uuid import uuid4
from datetime import datetime

from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from ai_2d_shared.scene import ContinuityState


class SceneModel(Base):
    __tablename__ = "scenes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    episode_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    continuity_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    transition_style: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'fade'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def continuity(self) -> ContinuityState:
        return ContinuityState(**self.continuity_json) if self.continuity_json else ContinuityState()
