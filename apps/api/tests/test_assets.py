import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def project(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Asset Test Project", "style": "2d_chinese_donghua", "aspect_ratio": "9:16"},
    )
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_list_assets_empty(client: AsyncClient, project: dict):
    resp = await client.get(f"/api/v1/projects/{project['id']}/assets")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_list_character_assets_empty(client: AsyncClient, project: dict):
    char_resp = await client.post(
        f"/api/v1/projects/{project['id']}/characters",
        json={"name": "Test Character", "role": "main"},
    )
    char_id = char_resp.json()["data"]["id"]
    resp = await client.get(f"/api/v1/characters/{char_id}/assets")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_get_asset_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/assets/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_asset_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/assets/00000000-0000-0000-0000-000000000000/download")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_asset_not_found(client: AsyncClient):
    resp = await client.delete("/api/v1/assets/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_assets_in_nonexistent_project(client: AsyncClient):
    resp = await client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000/assets")
    assert resp.status_code == 404
