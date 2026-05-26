"""add batch_id, depends_on, retry_count, error_type to jobs

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("batch_id", UUID(as_uuid=True),
                  sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True))
    op.add_column("jobs", sa.Column("depends_on", UUID(as_uuid=True),
                  sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True))
    op.add_column("jobs", sa.Column("retry_count", sa.Integer(),
                  nullable=False, server_default=sa.text("0")))
    op.add_column("jobs", sa.Column("error_type", sa.String(30), nullable=True))
    op.create_index("idx_jobs_batch_id", "jobs", ["batch_id"])
    op.create_index("idx_jobs_depends_on", "jobs", ["depends_on"])


def downgrade() -> None:
    op.drop_index("idx_jobs_depends_on")
    op.drop_index("idx_jobs_batch_id")
    op.drop_column("jobs", "error_type")
    op.drop_column("jobs", "retry_count")
    op.drop_column("jobs", "depends_on")
    op.drop_column("jobs", "batch_id")
