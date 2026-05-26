"""Tests for ImageGenService with mocked ComfyUIClient."""
from unittest.mock import AsyncMock

import pytest

from app.services.image_gen import ImageGenService, ImageGenError
from ai_2d_shared.character import CharacterDNA


@pytest.fixture
def dna() -> CharacterDNA:
    return CharacterDNA(
        age=22,
        gender="male",
        hair_color="black",
        hair_style="medium length",
        eye_color="gold",
        eye_shape="sharp",
        skin_tone="fair",
        build="lean athletic",
        clothing_style="modern casual",
    )


@pytest.mark.asyncio
async def test_generate_portrait_success(dna: CharacterDNA):
    service = ImageGenService()
    service.comfyui = AsyncMock()
    service.comfyui.generate_image = AsyncMock(return_value=b"fake_png_bytes")

    png = await service.generate_character_portrait(dna=dna, expression="neutral", pose="portrait")

    assert png == b"fake_png_bytes"
    service.comfyui.generate_image.assert_awaited_once()
    call_kwargs = service.comfyui.generate_image.call_args.kwargs
    assert "portrait of" in call_kwargs["positive_prompt"]
    assert "close-up portrait" in call_kwargs["positive_prompt"]
    assert "low quality, blurry" in call_kwargs["negative_prompt"]


@pytest.mark.asyncio
async def test_generate_portrait_with_expression(dna: CharacterDNA):
    service = ImageGenService()
    service.comfyui = AsyncMock()
    service.comfyui.generate_image = AsyncMock(return_value=b"png")

    await service.generate_character_portrait(dna=dna, expression="happy")
    prompt = service.comfyui.generate_image.call_args.kwargs["positive_prompt"]
    assert "smiling" in prompt
    assert "happy expression" in prompt


@pytest.mark.asyncio
async def test_generate_portrait_with_pose(dna: CharacterDNA):
    service = ImageGenService()
    service.comfyui = AsyncMock()
    service.comfyui.generate_image = AsyncMock(return_value=b"png")

    await service.generate_character_portrait(dna=dna, pose="action")
    prompt = service.comfyui.generate_image.call_args.kwargs["positive_prompt"]
    assert "dynamic action pose" in prompt


@pytest.mark.asyncio
async def test_generate_portrait_dimensions(dna: CharacterDNA):
    service = ImageGenService()
    service.comfyui = AsyncMock()
    service.comfyui.generate_image = AsyncMock(return_value=b"png")

    await service.generate_character_portrait(dna=dna, width=512, height=768)
    call_kwargs = service.comfyui.generate_image.call_args.kwargs
    assert call_kwargs["width"] == 512
    assert call_kwargs["height"] == 768


@pytest.mark.asyncio
async def test_generate_portrait_error(dna: CharacterDNA):
    service = ImageGenService()
    service.comfyui = AsyncMock()
    service.comfyui.generate_image = AsyncMock(side_effect=Exception("ComfyUI down"))

    with pytest.raises(ImageGenError, match="Image generation failed"):
        await service.generate_character_portrait(dna=dna)


@pytest.mark.asyncio
async def test_negative_prompt_always_present(dna: CharacterDNA):
    service = ImageGenService()
    service.comfyui = AsyncMock()
    service.comfyui.generate_image = AsyncMock(return_value=b"png")

    await service.generate_character_portrait(dna=dna)
    neg = service.comfyui.generate_image.call_args.kwargs["negative_prompt"]
    assert "low quality" in neg
    assert "blurry" in neg
    assert "nsfw" in neg
