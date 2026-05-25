import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def project(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Char Test Project", "style": "2d_chinese_donghua", "aspect_ratio": "9:16"},
    )
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_list_characters_empty(client: AsyncClient, project: dict):
    resp = await client.get(f"/api/v1/projects/{project['id']}/characters")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_create_character(client: AsyncClient, project: dict):
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/characters",
        json={
            "name": "Lâm Thiên Vũ",
            "role": "main_protagonist",
            "character_dna": {
                "age": 22,
                "gender": "male",
                "hair_color": "black",
                "eye_color": "gold",
                "personality_traits": ["calm", "observant", "principled"],
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "Lâm Thiên Vũ"
    assert data["role"] == "main_protagonist"
    assert data["character_dna"]["age"] == 22
    assert data["character_dna"]["hair_color"] == "black"


@pytest.mark.asyncio
async def test_get_character(client: AsyncClient, project: dict):
    create_resp = await client.post(
        f"/api/v1/projects/{project['id']}/characters",
        json={"name": "Tiêu Ngọc Minh", "role": "antagonist"},
    )
    char_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/api/v1/characters/{char_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Tiêu Ngọc Minh"


@pytest.mark.asyncio
async def test_update_character(client: AsyncClient, project: dict):
    create_resp = await client.post(
        f"/api/v1/projects/{project['id']}/characters",
        json={"name": "Old Name"},
    )
    char_id = create_resp.json()["data"]["id"]

    resp = await client.patch(
        f"/api/v1/characters/{char_id}",
        json={
            "name": "New Name",
            "role": "updated_role",
            "character_dna": {"hair_color": "blue"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "New Name"
    assert data["role"] == "updated_role"
    assert data["character_dna"]["hair_color"] == "blue"


@pytest.mark.asyncio
async def test_delete_character(client: AsyncClient, project: dict):
    create_resp = await client.post(
        f"/api/v1/projects/{project['id']}/characters",
        json={"name": "To Delete"},
    )
    char_id = create_resp.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/characters/{char_id}")
    assert resp.status_code == 204

    # Verify gone
    get_resp = await client.get(f"/api/v1/characters/{char_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_characters_multiple(client: AsyncClient, project: dict):
    await client.post(
        f"/api/v1/projects/{project['id']}/characters",
        json={"name": "Zeta", "role": "supporting"},
    )
    await client.post(
        f"/api/v1/projects/{project['id']}/characters",
        json={"name": "Alpha", "role": "main"},
    )
    await client.post(
        f"/api/v1/projects/{project['id']}/characters",
        json={"name": "Beta", "role": "main"},
    )

    resp = await client.get(f"/api/v1/projects/{project['id']}/characters")
    assert resp.status_code == 200
    chars = resp.json()["data"]
    assert len(chars) == 3
    # Ordered by name
    assert chars[0]["name"] == "Alpha"
    assert chars[1]["name"] == "Beta"
    assert chars[2]["name"] == "Zeta"


@pytest.mark.asyncio
async def test_character_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/characters/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_character_invalid_data(client: AsyncClient, project: dict):
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/characters",
        json={"name": ""},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_character_nonexistent_project(client: AsyncClient):
    resp = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/characters",
        json={"name": "Ghost"},
    )
    assert resp.status_code == 404
