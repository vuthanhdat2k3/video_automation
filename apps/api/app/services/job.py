from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_2d_shared.job import JobRead

from app.exceptions import NotFoundException
from app.models.job import JobModel


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        project_id: UUID,
        job_type: str,
        input_data: dict | None = None,
        batch_id: UUID | None = None,
        depends_on: UUID | None = None,
    ) -> JobRead:
        job = JobModel(
            project_id=project_id,
            type=job_type,
            input_json=input_data or {},
            status="pending",
            batch_id=batch_id,
            depends_on=depends_on,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return JobRead.model_validate(job)

    async def get(self, job_id: UUID) -> JobRead:
        result = await self.db.execute(select(JobModel).where(JobModel.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundException(f"Job {job_id} not found")
        return JobRead.model_validate(job)

    async def list_by_project(self, project_id: UUID) -> list[JobRead]:
        result = await self.db.execute(
            select(JobModel)
            .where(JobModel.project_id == project_id)
            .order_by(JobModel.created_at.desc())
        )
        return [JobRead.model_validate(j) for j in result.scalars().all()]

    async def update_status(self, job_id: UUID, status: str, progress: float | None = None) -> JobRead:
        job = await self._get_or_404(job_id)
        job.status = status
        if progress is not None:
            job.progress = progress
        await self.db.commit()
        await self.db.refresh(job)
        return JobRead.model_validate(job)

    async def complete(self, job_id: UUID, output_data: dict) -> JobRead:
        job = await self._get_or_404(job_id)
        job.status = "completed"
        job.progress = 1.0
        job.output_json = output_data
        await self.db.commit()
        await self.db.refresh(job)
        return JobRead.model_validate(job)

    async def fail(self, job_id: UUID, error_message: str) -> JobRead:
        job = await self._get_or_404(job_id)
        job.status = "failed"
        job.error = error_message
        await self.db.commit()
        await self.db.refresh(job)
        return JobRead.model_validate(job)

    async def _get_or_404(self, job_id: UUID) -> JobModel:
        result = await self.db.execute(select(JobModel).where(JobModel.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundException(f"Job {job_id} not found")
        return job
