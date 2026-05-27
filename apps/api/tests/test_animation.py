"""Tests for AnimationGenService with mocked ComfyUIClient."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.shot import ShotModel
from app.models.scene import SceneModel
from app.models.project import ProjectModel
from app.services.animation_gen import AnimationGenService, AnimationGenerationError


@pytest.mark.asyncio
async def test_generate_animation_no_shot(db_session):
    service = AnimationGenService(db_session)
    with pytest.raises(Exception):
        await service.generate_for_shot(uuid4())


@pytest.mark.asyncio
async def test_generate_animation_success(db_session):
    db = db_session
    project = ProjectModel(name="Test Project", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()

    scene = SceneModel(project_id=project.id, title="Scene 1", description="City view", order_index=0)
    db.add(scene)
    await db.flush()

    shot = ShotModel(scene_id=scene.id, order_index=0, duration_seconds=2.0, description="Samurai walks under the rain")
    db.add(shot)
    await db.commit()

    service = AnimationGenService(db)
    service.comfyui = AsyncMock()
    service.comfyui.generate_with_workflow = AsyncMock(return_value=b"fake_mp4_bytes")

    mp4_bytes, prompt = await service.generate_for_shot(shot.id)

    assert mp4_bytes == b"fake_mp4_bytes"
    assert "samurai" in prompt.lower()
    assert "Japanese animation" in prompt
    service.comfyui.generate_with_workflow.assert_awaited_once()
