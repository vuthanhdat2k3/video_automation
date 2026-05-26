"""Tests for TTS and audio generation services."""
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.tts import TTSService
from app.exceptions import NotFoundException
from app.models.scene import SceneModel
from app.models.shot import ShotModel


@pytest.mark.asyncio
async def test_tts_generate_for_shot(db_session):
    """Test TTS picks up shot description."""
    from app.models.project import ProjectModel
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()
    scene = SceneModel(project_id=project.id, title="S", order_index=0)
    db.add(scene)
    await db.flush()
    shot = ShotModel(scene_id=scene.id, order_index=0, duration_seconds=4.0,
                     description="Hero approaches the ancient temple")
    db.add(shot)
    await db.commit()
    await db.refresh(shot)

    svc = TTSService(db=db)
    svc.generate_speech = AsyncMock(return_value=b"fake_audio")

    audio, text = await svc.generate_for_shot(shot.id)
    assert audio == b"fake_audio"
    assert "ancient temple" in text
    svc.generate_speech.assert_awaited_once()


@pytest.mark.asyncio
async def test_tts_shot_not_found(db_session):
    svc = TTSService(db=db_session)
    with pytest.raises(NotFoundException):
        await svc.generate_for_shot("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_tts_edge_tts_provider():
    """Test edge_tts provider constructs correct call (mocked)."""
    svc = TTSService(provider="edge_tts")
    svc._generate_edge_tts = AsyncMock(return_value=b"edge_audio")
    result = await svc.generate_speech("Hello world", "vi-VN-NamMinhNeural")
    assert result == b"edge_audio"
    svc._generate_edge_tts.assert_awaited_once_with("Hello world", "vi-VN-NamMinhNeural")


@pytest.mark.asyncio
async def test_tts_openai_provider():
    """Test openai provider constructs correct call (mocked)."""
    svc = TTSService(provider="openai")
    svc._generate_openai = AsyncMock(return_value=b"openai_audio")
    result = await svc.generate_speech("Hello", "alloy")
    assert result == b"openai_audio"


@pytest.mark.asyncio
async def test_tts_shot_no_description(db_session):
    """Test fallback to generation_prompt."""
    from app.models.project import ProjectModel
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()
    scene = SceneModel(project_id=project.id, title="S", order_index=0)
    db.add(scene)
    await db.flush()
    shot = ShotModel(scene_id=scene.id, order_index=0, duration_seconds=4.0,
                     generation_prompt="A warrior fights a dragon")
    db.add(shot)
    await db.commit()
    await db.refresh(shot)

    svc = TTSService(db=db)
    svc.generate_speech = AsyncMock(return_value=b"audio")
    audio, text = await svc.generate_for_shot(shot.id)
    assert "warrior" in text
