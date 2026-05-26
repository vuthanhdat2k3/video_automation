import pytest
import pytest_asyncio
from httpx import AsyncClient
from ai_2d_shared.enums import ShotType


@pytest_asyncio.fixture
async def scene(client: AsyncClient) -> dict:
    proj = await client.post(
        "/api/v1/projects",
        json={"name": "Shot Test", "style": "2d_anime", "aspect_ratio": "9:16"},
    )
    pid = proj.json()["data"]["id"]
    resp = await client.post(
        f"/api/v1/projects/{pid}/scenes",
        json={"project_id": pid, "title": "Test Scene"},
    )
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_list_shots_empty(client: AsyncClient, scene: dict):
    resp = await client.get(f"/api/v1/scenes/{scene['id']}/shots")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_create_shot(client: AsyncClient, scene: dict):
    resp = await client.post(
        f"/api/v1/scenes/{scene['id']}/shots",
        json={
            "scene_id": scene["id"],
            "order_index": 0,
            "duration_seconds": 4.0,
            "description": "Opening shot",
            "shot_type": "cinematic_intro",
            "camera": {"angle": "low", "framing": "wide", "movement": "dolly"},
            "motion": {"animation_style": "live2d", "easing": "ease_in_out"},
            "audio": {"background_music": "ambient", "sound_effects": ["wind"]},
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["shot_type"] == "cinematic_intro"
    assert data["camera"]["angle"] == "low"
    assert data["motion"]["animation_style"] == "live2d"
    assert "wind" in data["audio"]["sound_effects"]


@pytest.mark.asyncio
async def test_get_shot(client: AsyncClient, scene: dict):
    create = await client.post(
        f"/api/v1/scenes/{scene['id']}/shots",
        json={"scene_id": scene["id"], "order_index": 0, "duration_seconds": 4.0},
    )
    sid = create.json()["data"]["id"]
    resp = await client.get(f"/api/v1/shots/{sid}")
    assert resp.status_code == 200
    assert resp.json()["data"]["duration_seconds"] == 4.0


@pytest.mark.asyncio
async def test_update_shot(client: AsyncClient, scene: dict):
    create = await client.post(
        f"/api/v1/scenes/{scene['id']}/shots",
        json={"scene_id": scene["id"], "order_index": 0, "duration_seconds": 4.0},
    )
    sid = create.json()["data"]["id"]
    resp = await client.patch(
        f"/api/v1/shots/{sid}",
        json={"duration_seconds": 6.0, "camera": {"angle": "high"}},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["duration_seconds"] == 6.0
    assert data["camera"]["angle"] == "high"


@pytest.mark.asyncio
async def test_delete_shot(client: AsyncClient, scene: dict):
    create = await client.post(
        f"/api/v1/scenes/{scene['id']}/shots",
        json={"scene_id": scene["id"], "order_index": 0, "duration_seconds": 4.0},
    )
    sid = create.json()["data"]["id"]
    resp = await client.delete(f"/api/v1/shots/{sid}")
    assert resp.status_code == 204
    get_resp = await client.get(f"/api/v1/shots/{sid}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_reorder_shots(client: AsyncClient, scene: dict):
    s1 = await client.post(
        f"/api/v1/scenes/{scene['id']}/shots",
        json={"scene_id": scene["id"], "order_index": 0, "duration_seconds": 4.0},
    )
    s2 = await client.post(
        f"/api/v1/scenes/{scene['id']}/shots",
        json={"scene_id": scene["id"], "order_index": 1, "duration_seconds": 4.0},
    )
    ids = [s2.json()["data"]["id"], s1.json()["data"]["id"]]
    resp = await client.patch(
        f"/api/v1/scenes/{scene['id']}/shots/reorder",
        json={"shot_ids": ids},
    )
    assert resp.status_code == 200
    order = [s["id"] for s in resp.json()["data"]]
    assert order == ids


@pytest.mark.asyncio
async def test_shot_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/shots/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_scene_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/scenes/00000000-0000-0000-0000-000000000000/shots")
    assert resp.status_code == 200  # empty list is valid
    assert resp.json()["data"] == []
