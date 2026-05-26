"""add shot asset link columns

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shots", sa.Column("background_asset_id", UUID(as_uuid=True),
                  sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True))
    op.add_column("shots", sa.Column("keyframe_asset_id", UUID(as_uuid=True),
                  sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True))
    op.add_column("shots", sa.Column("generation_prompt", sa.Text, nullable=True))
    op.add_column("shots", sa.Column("generation_params", JSONB,
                  nullable=False, server_default=sa.text("'{}'::jsonb")))


def downgrade() -> None:
    op.drop_column("shots", "generation_params")
    op.drop_column("shots", "generation_prompt")
    op.drop_column("shots", "keyframe_asset_id")
    op.drop_column("shots", "background_asset_id")
