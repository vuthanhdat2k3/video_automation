import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def project(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Job Test", "style": "2d_anime", "aspect_ratio": "9:16"},
    )
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_materialize_story_bible(client: AsyncClient, project: dict):
    # Seed story bible directly
    import sqlalchemy as sa
    from app.database import get_db
    from app.models.project import ProjectModel

    async for db in get_db():
        result = await db.execute(sa.select(ProjectModel).where(ProjectModel.id == project["id"]))
        p = result.scalar_one_or_none()
        p.story_json = {
            "scene_breakdowns": [
                {"episode_number": 1, "scene_order": 0, "title": "Intro",
                 "description": "City view", "duration_seconds": 10.0,
                 "characters_present": [], "location": "city", "emotional_beat": "calm"},
                {"episode_number": 1, "scene_order": 1, "title": "Confrontation",
                 "description": "Face off", "duration_seconds": 15.0,
                 "characters_present": [], "location": "rooftop", "emotional_beat": "intense"},
            ]
        }
        await db.commit()
        break

    resp = await client.post(f"/api/v1/projects/{project['id']}/story/materialize")
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["created_scenes"] == 2
    assert data["created_shots"] == 2


@pytest.mark.asyncio
async def test_materialize_no_story_bible(client: AsyncClient, project: dict):
    resp = await client.post(f"/api/v1/projects/{project['id']}/story/materialize")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_materialize_nonexistent_project(client: AsyncClient):
    resp = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/story/materialize"
    )
    assert resp.status_code == 404
