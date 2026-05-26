"""ARQ queue client for job dispatch."""
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings
from app.services.job import JobService
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.job import JobRead


_pool = None


async def get_queue():
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool


async def close_queue():
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


async def dispatch_job(
    db: AsyncSession,
    project_id: UUID,
    job_type: str,
    task_name: str,
    batch_id: UUID | None = None,
    depends_on: UUID | None = None,
    input_data: dict | None = None,
) -> JobRead:
    """Create a JobModel then enqueue an ARQ task. Returns JobRead."""
    job_svc = JobService(db)
    job = await job_svc.create(
        project_id, job_type, input_data or {},
        batch_id=batch_id, depends_on=depends_on,
    )

    queue = await get_queue()
    await queue.enqueue_job(
        task_name,
        _job_id=str(job.id),
        project_id=str(project_id),
        **{k: str(v) for k, v in (input_data or {}).items()},
    )

    return job
