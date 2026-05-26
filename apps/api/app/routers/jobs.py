"""Jobs CRUD router."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import NotFoundException
from app.models.project import ProjectModel
from app.services.job import JobService
from sqlalchemy import select

router = APIRouter()


@router.get("/projects/{project_id}/jobs", response_model=dict)
async def list_jobs(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all jobs for a project."""
    proj_result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    if not proj_result.scalar_one_or_none():
        raise NotFoundException(f"Project {project_id} not found")

    svc = JobService(db)
    jobs = await svc.list_by_project(project_id)
    return {"data": [j.model_dump() for j in jobs], "error": None}


@router.get("/jobs/{job_id}", response_model=dict)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get job status and result."""
    svc = JobService(db)
    job = await svc.get(job_id)
    return {"data": job.model_dump(), "error": None}
