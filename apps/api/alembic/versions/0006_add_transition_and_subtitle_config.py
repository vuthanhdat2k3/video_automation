"""add transition_style to scenes and subtitle config to projects

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scenes", sa.Column("transition_style", sa.String(20),
                  nullable=False, server_default="fade"))
    op.add_column("projects", sa.Column("default_font", sa.String(100),
                  nullable=False, server_default="Noto Sans SC"))
    op.add_column("projects", sa.Column("subtitle_enabled", sa.Boolean(),
                  nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("projects", "subtitle_enabled")
    op.drop_column("projects", "default_font")
    op.drop_column("scenes", "transition_style")
