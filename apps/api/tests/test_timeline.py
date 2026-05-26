import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def project(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Timeline Test", "style": "2d_anime", "aspect_ratio": "9:16"},
    )
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_project_timeline(client: AsyncClient, project: dict):
    # Create scene + shots
    scene_resp = await client.post(
        f"/api/v1/projects/{project['id']}/scenes",
        json={"project_id": project["id"], "title": "S1", "duration_seconds": 10.0},
    )
    sid = scene_resp.json()["data"]["id"]

    await client.post(
        f"/api/v1/scenes/{sid}/shots",
        json={"scene_id": sid, "order_index": 0, "duration_seconds": 4.0},
    )
    await client.post(
        f"/api/v1/scenes/{sid}/shots",
        json={"scene_id": sid, "order_index": 1, "duration_seconds": 6.0},
    )

    resp = await client.get(f"/api/v1/projects/{project['id']}/timeline")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["scene_count"] >= 1
    assert data["total_duration"] >= 10.0


@pytest.mark.asyncio
async def test_scene_timeline(client: AsyncClient, project: dict):
    scene_resp = await client.post(
        f"/api/v1/projects/{project['id']}/scenes",
        json={"project_id": project["id"], "title": "S2", "duration_seconds": 8.0},
    )
    sid = scene_resp.json()["data"]["id"]

    await client.post(
        f"/api/v1/scenes/{sid}/shots",
        json={"scene_id": sid, "order_index": 0, "duration_seconds": 3.0},
    )
    await client.post(
        f"/api/v1/scenes/{sid}/shots",
        json={"scene_id": sid, "order_index": 1, "duration_seconds": 5.0},
    )

    resp = await client.get(f"/api/v1/scenes/{sid}/timeline")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["shot_count"] == 2
    assert data["total_duration"] == 8.0
    assert data["shots"][0]["start_at"] == 0.0
    assert data["shots"][0]["end_at"] == 3.0
    assert data["shots"][1]["start_at"] == 3.0
    assert data["shots"][1]["end_at"] == 8.0
