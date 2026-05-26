"""add post-production config columns to scenes and shots

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scenes", sa.Column("grade_json", JSONB, nullable=False,
                  server_default=sa.text("'{}'::jsonb")))
    op.add_column("scenes", sa.Column("vfx_json", JSONB, nullable=False,
                  server_default=sa.text("'{}'::jsonb")))
    op.add_column("scenes", sa.Column("shadow_enabled", sa.Boolean(),
                  nullable=False, server_default=sa.text("false")))
    op.add_column("shots", sa.Column("overlay_json", JSONB, nullable=False,
                  server_default=sa.text("'{}'::jsonb")))


def downgrade() -> None:
    op.drop_column("shots", "overlay_json")
    op.drop_column("scenes", "shadow_enabled")
    op.drop_column("scenes", "vfx_json")
    op.drop_column("scenes", "grade_json")
