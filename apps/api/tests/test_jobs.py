"""Tests for job queue and router."""
from unittest.mock import patch, AsyncMock

import pytest

from app.services.job import JobService
from app.exceptions import NotFoundException
from app.models.project import ProjectModel


@pytest.mark.asyncio
async def test_job_create(db_session):
    """Test creating a job via JobService."""
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()

    svc = JobService(db)
    job = await svc.create(project.id, "generate_keyframe", {"shot_id": "abc"})
    assert job.type == "generate_keyframe"
    assert job.status == "pending"
    assert job.project_id == project.id


@pytest.mark.asyncio
async def test_job_get(db_session):
    """Test getting a job by ID."""
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()

    svc = JobService(db)
    created = await svc.create(project.id, "export", {"scene_id": "xyz"})
    fetched = await svc.get(created.id)
    assert fetched.id == created.id
    assert fetched.type == "export"


@pytest.mark.asyncio
async def test_job_not_found(db_session):
    svc = JobService(db_session)
    with pytest.raises(NotFoundException):
        await svc.get("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_job_complete(db_session):
    """Test completing a job."""
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()

    svc = JobService(db)
    created = await svc.create(project.id, "export", {})
    completed = await svc.complete(created.id, {"url": "/storage/test.mp4"})
    assert completed.status == "completed"
    assert completed.output_data["url"] == "/storage/test.mp4"


@pytest.mark.asyncio
async def test_job_fail(db_session):
    """Test failing a job."""
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()

    svc = JobService(db)
    created = await svc.create(project.id, "generate_background", {})
    failed = await svc.fail(created.id, "ComfyUI timeout")
    assert failed.status == "failed"
    assert "timeout" in failed.error


@pytest.mark.asyncio
async def test_jobs_list_by_project(db_session):
    """Test listing jobs for a project."""
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()

    svc = JobService(db)
    await svc.create(project.id, "generate_keyframe", {})
    await svc.create(project.id, "generate_audio", {})

    jobs = await svc.list_by_project(project.id)
    assert len(jobs) == 2


@pytest.mark.asyncio
async def test_jobs_router_list(client, db_session):
    """Test GET /projects/{id}/jobs."""
    from app.models.project import ProjectModel
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    svc = JobService(db)
    await svc.create(project.id, "export", {})
    await db.commit()

    resp = await client.get(f"/api/v1/projects/{project.id}/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1


@pytest.mark.asyncio
async def test_jobs_router_get(client, db_session):
    """Test GET /jobs/{id}."""
    from app.models.project import ProjectModel
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    svc = JobService(db)
    created = await svc.create(project.id, "generate_background", {})
    await svc.complete(created.id, {"url": "test"})
    await db.commit()
    await db.refresh(created) if False else None

    resp = await client.get(f"/api/v1/jobs/{created.id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_jobs_router_project_not_found(client):
    """Test 404 for non-existent project."""
    resp = await client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/jobs"
    )
    assert resp.status_code == 404
