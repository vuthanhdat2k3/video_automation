import pytest
import pytest_asyncio
from httpx import AsyncClient
from ai_2d_shared.scene import ContinuityState


@pytest_asyncio.fixture
async def project(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Scene Test", "style": "2d_anime", "aspect_ratio": "9:16"},
    )
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_list_scenes_empty(client: AsyncClient, project: dict):
    resp = await client.get(f"/api/v1/projects/{project['id']}/scenes")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_create_scene(client: AsyncClient, project: dict):
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/scenes",
        json={
            "project_id": project["id"],
            "title": "Opening Scene",
            "description": "The city at dawn",
            "duration_seconds": 12.0,
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["title"] == "Opening Scene"
    assert data["order_index"] == 0


@pytest.mark.asyncio
async def test_create_scene_with_continuity(client: AsyncClient, project: dict):
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/scenes",
        json={
            "project_id": project["id"],
            "title": "Night Scene",
            "description": "Under the moonlight",
            "duration_seconds": 15.0,
            "continuity": {
                "lighting": "moonlight",
                "mood": "mysterious",
                "time_of_day": "night",
                "weather": "clear",
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["continuity"]["lighting"] == "moonlight"
    assert data["continuity"]["mood"] == "mysterious"


@pytest.mark.asyncio
async def test_get_scene(client: AsyncClient, project: dict):
    create = await client.post(
        f"/api/v1/projects/{project['id']}/scenes",
        json={"project_id": project["id"], "title": "Get Me"},
    )
    sid = create.json()["data"]["id"]
    resp = await client.get(f"/api/v1/scenes/{sid}")
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "Get Me"
    assert "shots" in resp.json()["data"]


@pytest.mark.asyncio
async def test_update_scene(client: AsyncClient, project: dict):
    create = await client.post(
        f"/api/v1/projects/{project['id']}/scenes",
        json={"project_id": project["id"], "title": "Old Title"},
    )
    sid = create.json()["data"]["id"]
    resp = await client.patch(
        f"/api/v1/scenes/{sid}",
        json={"title": "New Title", "duration_seconds": 20.0},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "New Title"
    assert data["duration_seconds"] == 20.0


@pytest.mark.asyncio
async def test_delete_scene(client: AsyncClient, project: dict):
    create = await client.post(
        f"/api/v1/projects/{project['id']}/scenes",
        json={"project_id": project["id"], "title": "Delete Me"},
    )
    sid = create.json()["data"]["id"]
    resp = await client.delete(f"/api/v1/scenes/{sid}")
    assert resp.status_code == 204
    get_resp = await client.get(f"/api/v1/scenes/{sid}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_reorder_scenes(client: AsyncClient, project: dict):
    s1 = await client.post(
        f"/api/v1/projects/{project['id']}/scenes",
        json={"project_id": project["id"], "title": "A"},
    )
    s2 = await client.post(
        f"/api/v1/projects/{project['id']}/scenes",
        json={"project_id": project["id"], "title": "B"},
    )
    s3 = await client.post(
        f"/api/v1/projects/{project['id']}/scenes",
        json={"project_id": project["id"], "title": "C"},
    )
    ids = [s3.json()["data"]["id"], s2.json()["data"]["id"], s1.json()["data"]["id"]]
    resp = await client.patch(
        f"/api/v1/projects/{project['id']}/scenes/reorder",
        json={"scene_ids": ids},
    )
    assert resp.status_code == 200
    order = [s["id"] for s in resp.json()["data"]]
    assert order == ids


@pytest.mark.asyncio
async def test_scene_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/scenes/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
