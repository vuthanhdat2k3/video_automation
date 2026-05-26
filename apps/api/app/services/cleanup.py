"""Job cleanup service — removes old jobs and orphaned assets."""
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobModel


async def cleanup_old_jobs(
    db: AsyncSession,
    max_age_hours: int = 168,
) -> int:
    """Delete completed/failed jobs older than max_age_hours. Returns count deleted."""
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    result = await db.execute(
        select(JobModel).where(
            JobModel.status.in_(["completed", "failed"]),
            JobModel.updated_at < cutoff,
        )
    )
    jobs = result.scalars().all()
    count = len(jobs)
    for job in jobs:
        await db.delete(job)
    await db.commit()
    return count
