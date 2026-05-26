"""add shot audio and video export columns

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shots", sa.Column("audio_asset_id", UUID(as_uuid=True),
                  sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True))
    op.add_column("shots", sa.Column("video_export_id", UUID(as_uuid=True),
                  sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True))


def downgrade() -> None:
    op.drop_column("shots", "video_export_id")
    op.drop_column("shots", "audio_asset_id")
