"""Tests for background and keyframe generation with mocked ComfyUI."""
from unittest.mock import AsyncMock

import pytest

from app.services.background_gen import BackgroundGenService
from app.services.keyframe_gen import KeyframeGenService
from app.exceptions import NotFoundException
from app.models.scene import SceneModel


@pytest.mark.asyncio
async def test_background_prompt_construction(db_session):
    """Test background prompt is built from scene continuity."""
    from app.models.project import ProjectModel
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()
    scene = SceneModel(
        project_id=project.id,
        title="Forest Clearing",
        description="A magical forest with glowing plants",
        order_index=0,
        continuity_json={
            "time_of_day": "night",
            "weather": "clear",
            "location": "enchanted forest",
            "lighting": "bioluminescent",
            "mood": "mystical",
        },
    )
    db.add(scene)
    await db.flush()
    scene_id = scene.id
    await db.commit()

    # Mock comfyui
    svc = BackgroundGenService(db)
    svc.comfyui = AsyncMock()
    svc.comfyui.generate_with_workflow = AsyncMock(return_value=b"fake_png")

    png, prompt = await svc.generate_for_scene(scene_id)
    assert png == b"fake_png"
    assert "night" in prompt
    assert "bioluminescent" in prompt
    assert "mystical" in prompt
    assert "no characters" in prompt


@pytest.mark.asyncio
async def test_background_scene_not_found(db_session):
    svc = BackgroundGenService(db_session)
    with pytest.raises(NotFoundException):
        await svc.generate_for_scene("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_keyframe_prompt_construction(db_session):
    """Test keyframe prompt includes camera config and shot description."""
    from app.models.project import ProjectModel
    from app.models.shot import ShotModel
    db = db_session
    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()
    scene = SceneModel(project_id=project.id, title="Test", order_index=0)
    db.add(scene)
    await db.flush()

    shot = ShotModel(
        scene_id=scene.id,
        order_index=0,
        duration_seconds=4.0,
        description="Hero enters the room",
        shot_type="cinematic_intro",
        camera_json={"angle": "low", "framing": "wide", "movement": "dolly"},
        motion_json={"animation_style": "live2d"},
        audio_json={},
    )
    db.add(shot)
    await db.flush()
    shot_id = shot.id
    await db.commit()

    svc = KeyframeGenService(db)
    svc.comfyui = AsyncMock()
    svc.comfyui.generate_with_workflow = AsyncMock(return_value=b"fake_png")

    png, prompt = await svc.generate_for_shot(shot_id)
    assert png == b"fake_png"
    assert "Hero enters the room" in prompt
    assert "low angle" in prompt
    assert "wide framing" in prompt
    assert "dolly" in prompt


@pytest.mark.asyncio
async def test_keyframe_shot_not_found(db_session):
    svc = KeyframeGenService(db_session)
    with pytest.raises(NotFoundException):
        await svc.generate_for_shot("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_generate_shot_background_endpoint(client, db_session):
    """Test POST /shots/{id}/generate-background via API (mocked dispatch)."""
    from app.models.project import ProjectModel
    db = db_session
    from unittest.mock import patch, AsyncMock
    from app.models.shot import ShotModel

    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()
    scene = SceneModel(project_id=project.id, title="BG Test", order_index=0)
    db.add(scene)
    await db.flush()
    shot = ShotModel(scene_id=scene.id, order_index=0, duration_seconds=4.0)
    db.add(shot)
    await db.commit()
    await db.refresh(shot)

    with patch("app.routers.shots.dispatch_job", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value.id = shot.id
        resp = await client.post(f"/api/v1/shots/{shot.id}/generate-background")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "job_id" in data


@pytest.mark.asyncio
async def test_generate_shot_keyframe_endpoint(client, db_session):
    """Test POST /shots/{id}/generate-keyframe via API (mocked dispatch)."""
    from app.models.project import ProjectModel
    db = db_session
    from unittest.mock import patch, AsyncMock
    from app.models.shot import ShotModel

    project = ProjectModel(name="Test", style="2d_anime", aspect_ratio="9:16")
    db.add(project)
    await db.flush()
    scene = SceneModel(project_id=project.id, title="KF Test", order_index=0)
    db.add(scene)
    await db.flush()
    shot = ShotModel(scene_id=scene.id, order_index=0, duration_seconds=4.0)
    db.add(shot)
    await db.commit()
    await db.refresh(shot)

    with patch("app.routers.shots.dispatch_job", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value.id = shot.id
        resp = await client.post(f"/api/v1/shots/{shot.id}/generate-keyframe")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "job_id" in data
