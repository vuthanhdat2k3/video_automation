"""Job cleanup service — removes old jobs."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobModel
from app.database import async_session_factory
from app.logging import get_logger

logger = get_logger("cleanup")


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


async def cleanup_cron_task(ctx) -> None:
    """ARQ cron task: clean up completed/failed jobs older than 7 days."""
    async with async_session_factory() as db:
        deleted = await cleanup_old_jobs(db, max_age_hours=168)
        logger.info("cleanup_cron_task completed", extra={"deleted_count": deleted})
