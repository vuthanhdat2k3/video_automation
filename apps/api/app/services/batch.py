"""Batch job grouping service."""
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.job import JobService
from app.models.job import JobModel
from ai_2d_shared.job import JobRead


class BatchJobService:
    """Manage parent batch jobs that track aggregate progress of children."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._job_svc = JobService(db)

    async def create_batch(
        self,
        project_id: UUID,
        batch_type: str,
        children: list[dict],
    ) -> tuple[JobRead, list[JobRead]]:
        """Create a batch parent + children. Returns (parent, child_jobs)."""
        parent = await self._job_svc.create(project_id, "batch", {
            "batch_type": batch_type,
            "total": len(children),
            "completed": 0,
            "failed": 0,
        })

        child_jobs = []
        for c in children:
            cj = await self._job_svc.create(
                project_id,
                c.get("job_type", "unknown"),
                c.get("input_data", {}),
                batch_id=parent.id,
                depends_on=c.get("depends_on"),
            )
            child_jobs.append(cj)

        return parent, child_jobs

    async def on_child_complete(self, child_job_id: UUID) -> JobRead | None:
        """Update parent progress when a child completes. Returns parent if batch fully done."""
        child = (await self.db.execute(
            select(JobModel).where(JobModel.id == child_job_id)
        )).scalar_one_or_none()
        if not child or not child.batch_id:
            return None

        parent = (await self.db.execute(
            select(JobModel).where(JobModel.id == child.batch_id)
        )).scalar_one_or_none()
        if not parent:
            return None

        total = parent.input_json.get("total", 1)
        done = await self.db.scalar(
            select(func.count()).select_from(JobModel).where(
                JobModel.batch_id == child.batch_id, JobModel.status == "completed"
            )
        ) or 0
        fail_count = await self.db.scalar(
            select(func.count()).select_from(JobModel).where(
                JobModel.batch_id == child.batch_id, JobModel.status == "failed"
            )
        ) or 0

        parent.input_json["completed"] = done
        parent.input_json["failed"] = fail_count
        parent.progress = (done / total) if total > 0 else 0

        if done + fail_count >= total:
            parent.status = "completed"
            parent.progress = 1.0

        await self.db.commit()
        await self.db.refresh(parent)
        return JobRead.model_validate(parent)

    async def on_child_failed(self, child_job_id: UUID) -> JobRead | None:
        """Update parent when a child fails. Returns parent if batch fully done."""
        child = (await self.db.execute(
            select(JobModel).where(JobModel.id == child_job_id)
        )).scalar_one_or_none()
        if not child or not child.batch_id:
            return None

        parent = await self.db.get(JobModel, child.batch_id)
        if not parent:
            return None

        return await self.on_child_complete(child_job_id)
