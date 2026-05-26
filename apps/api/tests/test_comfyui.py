"""Tests for ComfyUIClient with mocked HTTP."""
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.comfyui.client import ComfyUIClient, ComfyUIClientError


@pytest.fixture
def client() -> ComfyUIClient:
    return ComfyUIClient(base_url="http://test-comfyui:8188", timeout=10)


def _make_response(status_code: int, json_data: dict | None = None, content: bytes | None = None) -> httpx.Response:
    req = httpx.Request("POST", "http://test-comfyui:8188/prompt")
    return httpx.Response(status_code=status_code, request=req, json=json_data, content=content)


@pytest.mark.asyncio
async def test_generate_image_success(client: ComfyUIClient):
    mock_post = AsyncMock()
    mock_post.return_value = _make_response(200, json_data={"prompt_id": "abc-123"})

    def mock_get_side(url, *args, **kwargs):
        url_str = str(url)
        if "/history/abc-123" in url_str:
            return _make_response(
                200,
                json_data={
                    "abc-123": {
                        "status": {"completed": True},
                        "outputs": {
                            "9": {
                                "images": [{"filename": "test.png", "subfolder": "", "type": "output"}]
                            }
                        },
                    }
                },
            )
        if "/view" in url_str:
            return _make_response(200, content=b"pngbytes")
        return _make_response(404)

    mock_get = AsyncMock(side_effect=mock_get_side)

    with (
        patch("httpx.AsyncClient.post", mock_post),
        patch("httpx.AsyncClient.get", mock_get),
    ):
        png = await client.generate_image(positive_prompt="test girl", negative_prompt="bad", seed=42)
        assert png == b"pngbytes"


@pytest.mark.asyncio
async def test_generate_image_timeout(client: ComfyUIClient):
    mock_post = AsyncMock()
    mock_post.return_value = _make_response(200, json_data={"prompt_id": "timeout-id"})

    mock_get = AsyncMock()
    mock_get.return_value = _make_response(404)

    with (
        patch("httpx.AsyncClient.post", mock_post),
        patch("httpx.AsyncClient.get", mock_get),
    ):
        with pytest.raises(ComfyUIClientError, match="Timeout"):
            await client.generate_image(positive_prompt="test", seed=1)


@pytest.mark.asyncio
async def test_workflow_errors_raised(client: ComfyUIClient):
    mock_post = AsyncMock()
    mock_post.return_value = _make_response(
        200,
        json_data={
            "prompt_id": "err-id",
            "node_errors": {"3": {"class_type": "KSampler", "errors": ["Missing input"]}},
        },
    )

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(ComfyUIClientError, match="Workflow errors"):
            await client.generate_image(positive_prompt="test", seed=1)


@pytest.mark.asyncio
async def test_build_workflow_injects_params(client: ComfyUIClient):
    workflow = client._build_workflow(
        positive_prompt="a cat",
        negative_prompt="blurry",
        width=1024,
        height=1536,
        seed=42,
        steps=25,
        cfg=5.0,
        ckpt_name="animagine-xl-4.0-opt.safetensors",
    )

    assert workflow["4"]["inputs"]["ckpt_name"] == "animagine-xl-4.0-opt.safetensors"
    assert workflow["5"]["inputs"]["width"] == 1024
    assert workflow["5"]["inputs"]["height"] == 1536
    assert workflow["3"]["inputs"]["seed"] == 42
    assert workflow["3"]["inputs"]["steps"] == 25
    assert workflow["3"]["inputs"]["cfg"] == 5.0
    assert workflow["6"]["inputs"]["text"] == "a cat"
    assert workflow["7"]["inputs"]["text"] == "blurry"
    assert workflow["3"]["inputs"]["model"] == ["4", 0]
    assert workflow["3"]["inputs"]["positive"] == ["6", 0]
    assert workflow["3"]["inputs"]["negative"] == ["7", 0]
    assert workflow["3"]["inputs"]["latent_image"] == ["5", 0]
    assert workflow["8"]["inputs"]["samples"] == ["3", 0]
    assert workflow["8"]["inputs"]["vae"] == ["4", 2]


@pytest.mark.asyncio
async def test_default_seed_changes_each_call(client: ComfyUIClient):
    with patch("httpx.AsyncClient.send", new=AsyncMock(return_value=httpx.Response(200, json={"prompt_id": "x"}))):
        with patch.object(client, "_wait_for_result", new=AsyncMock(return_value={"outputs": {}})):
            with patch.object(client, "_download_image", new=AsyncMock(return_value=b"x")):
                wf1 = client._build_workflow("a", "", 512, 512, int(1000 % 2**32), 20, 7.0, "ckpt")
                wf2 = client._build_workflow("a", "", 512, 512, int(2000 % 2**32), 20, 7.0, "ckpt")
                assert wf1["3"]["inputs"]["seed"] != wf2["3"]["inputs"]["seed"]
