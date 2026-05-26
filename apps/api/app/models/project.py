from uuid import uuid4
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    style: Mapped[str] = mapped_column(String(50), nullable=False, server_default="2d_chinese_donghua")
    aspect_ratio: Mapped[str] = mapped_column(String(10), nullable=False, server_default="9:16")
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    story_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    default_font: Mapped[str] = mapped_column(String(100), nullable=False, server_default="Noto Sans SC")
    subtitle_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
