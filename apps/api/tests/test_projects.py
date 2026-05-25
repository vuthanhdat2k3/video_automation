import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient):
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Test Project",
            "style": "2d_chinese_donghua",
            "aspect_ratio": "9:16",
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Test Project"
    assert data["status"] == "draft"
    assert data["style"] == "2d_chinese_donghua"


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient):
    # Create two projects
    await client.post("/api/v1/projects", json={"name": "Project A", "style": "2d_anime"})
    await client.post("/api/v1/projects", json={"name": "Project B", "style": "2d_western"})

    response = await client.get("/api/v1/projects")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient):
    create_resp = await client.post("/api/v1/projects", json={"name": "My Project"})
    project_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "My Project"


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient):
    create_resp = await client.post("/api/v1/projects", json={"name": "Old Name"})
    project_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "New Name", "description": "Updated description"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "New Name"
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient):
    create_resp = await client.post("/api/v1/projects", json={"name": "To Delete"})
    project_id = create_resp.json()["data"]["id"]

    response = await client.delete(f"/api/v1/projects/{project_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/api/v1/projects/{project_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_create_project_invalid_data(client: AsyncClient):
    response = await client.post("/api/v1/projects", json={"name": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_nonexistent_project(client: AsyncClient):
    response = await client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["error"] is not None
