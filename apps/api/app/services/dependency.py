"""Dependency checker for job execution ordering."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobModel


class DependencyFailedError(Exception):
    """Dependency job failed — this job should not run."""
    pass


class RequeueWithDelayError(Exception):
    """Dependency not ready — requeue this job after a delay."""
    def __init__(self, delay: int = 30):
        self.delay = delay
        super().__init__(f"Requeue with {delay}s delay")


class DependencyChecker:
    """Check if a job's dependencies are satisfied before execution."""

    @staticmethod
    async def is_ready(db: AsyncSession, depends_on: UUID) -> bool:
        result = await db.execute(select(JobModel).where(JobModel.id == depends_on))
        dep = result.scalar_one_or_none()
        return dep is not None and dep.status == "completed"

    @staticmethod
    async def is_blocked(db: AsyncSession, depends_on: UUID) -> bool:
        result = await db.execute(select(JobModel).where(JobModel.id == depends_on))
        dep = result.scalar_one_or_none()
        return dep is not None and dep.status == "failed"

    @staticmethod
    async def check(db: AsyncSession, depends_on: UUID | None) -> None:
        """Raise DependencyFailedError or RequeueWithDelayError if not ready."""
        if depends_on is None:
            return
        if await DependencyChecker.is_blocked(db, depends_on):
            raise DependencyFailedError(f"Dependency {depends_on} failed")
        if not await DependencyChecker.is_ready(db, depends_on):
            raise RequeueWithDelayError(30)
